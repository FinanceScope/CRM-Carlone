/* CRM Entreprises Nièvre, version autonome (sans claude.ai) : connexion Firebase, données et suivi dans Firestore.
   La page publique ne contient que cet écran de connexion. Après connexion d'un associé autorisé (règles Firestore), le CRM
   (donnees/app), les fiches (donnees/entreprises-NN) et les prospects culture (donnees/culture) sont lus dans Firestore, puis la
   page du CRM est écrite à la place de celle-ci. Le CRM y trouve window.claude.use("db") et use("user") avec la même interface
   que sur claude.ai : son code est le même dans les deux versions. */
(function () {
  "use strict";
  var CFG = window.CRM_CONFIG || {};
  var $ = function (s) { return document.querySelector(s); };
  var gate = $("#gate"), msg = $("#gmsg");
  function say(t, kind) { msg.textContent = t || ""; msg.className = "gmsg" + (kind ? " " + kind : ""); }
  function show(id) { ["#gLogin", "#gWait", "#gUpload", "#gDenied"].forEach(function (s) { var e = $(s); if (e) e.hidden = s !== id; }); }
  if (!CFG.firebase || !CFG.firebase.apiKey || /A_REMPLACER/.test(CFG.firebase.apiKey)) {
    show("#gWait"); $("#gWaitTxt").textContent = "Configuration absente : remplir public/config.js avec la configuration du projet Firebase (voir le guide d'installation).";
    return;
  }
  firebase.initializeApp(CFG.firebase);
  var auth = firebase.auth(), fs = firebase.firestore();
  if (CFG.emulateurs) { auth.useEmulator("http://127.0.0.1:" + (CFG.emulateurs.auth || 9099), { disableWarnings: true }); fs.useEmulator("127.0.0.1", CFG.emulateurs.firestore || 8080); }
  var FP = firebase.firestore.FieldPath, FV = firebase.firestore.FieldValue;
  window.CRM_URL = location.origin + location.pathname.replace(/index\.html$/, "");
  window.CRM_ETUDE = "etude-hermes.html";

  /* ---------- Base partagée : même interface que claude.ai (collection, doc, get, set, update fusionnant, onSnapshot) ---------- */
  var isObj = function (v) { return v && typeof v === "object" && !Array.isArray(v); };
  function flatten(o, pre, out) {   // { journal: { id1: {...} } } -> chemin journal.id1 ; null -> champ supprimé
    Object.keys(o).forEach(function (k) {
      var v = o[k], p = pre.concat([k]);
      if (isObj(v)) { if (Object.keys(v).length) flatten(v, p, out); }
      else out.push(new FP(p[0], ...p.slice(1)), v === null ? FV.delete() : v);
    });
    return out;
  }
  function clean(o) { var r = {}; Object.keys(o).forEach(function (k) { var v = o[k]; if (v === null || v === undefined) return; r[k] = isObj(v) ? clean(v) : v; }); return r; }
  function err(e) { var c = e && e.code, x = new Error((e && e.message) || String(e)); x.code = c === "not-found" ? "invalid_argument" : c === "permission-denied" ? "permission_denied" : c; return x; }
  function wrapSnap(d) { return { id: d.id, exists: d.exists, data: function () { return d.data(); } }; }
  function docRef(col, id) {
    var r = fs.collection(col).doc(id);
    return {
      get: function () { return r.get().then(wrapSnap, function (e) { throw err(e); }); },
      set: function (v) { return r.set(clean(v)).catch(function (e) { throw err(e); }); },
      update: function (v) { var a = flatten(v, [], []); if (!a.length) return Promise.resolve(); return r.update.apply(r, a).catch(function (e) { throw err(e); }); },
      delete: function () { return r.delete().catch(function (e) { throw err(e); }); }
    };
  }
  var dbShim = {
    collection: function (col) {
      return {
        doc: function (id) { return docRef(col, id); },
        onSnapshot: function (cb, ecb) {
          return fs.collection(col).onSnapshot(function (s) { cb({ docs: s.docs.map(wrapSnap), metadata: { fromCache: s.metadata.fromCache } }); },
            function (e) { if (ecb) ecb(err(e)); });
        }
      };
    }
  };
  var noms = {};
  var userShim = {
    id: function () { return Promise.resolve(auth.currentUser ? auth.currentUser.uid : null); },
    can: function () { return Promise.resolve(true); },   // les règles Firestore décident ; un refus d'écriture est géré par le CRM
    isOwner: function () { return false; },
    profiles: function (ids) {
      var out = {};
      return Promise.all((ids || []).map(function (id) {
        if (noms[id] !== undefined) { out[id] = { name: noms[id] }; return null; }
        return fs.collection("membres").doc(id).get().then(function (d) { noms[id] = d.exists ? (d.data().nom || "") : ""; out[id] = { name: noms[id] }; }, function () { out[id] = { name: "" }; });
      })).then(function () { return out; });
    }
  };

  /* ---------- Données du CRM dans Firestore ---------- */
  var TAILLE = 60;   // entreprises par document (un document Firestore fait au plus 1 Mo)
  function lireDonnees() {
    return fs.collection("donnees").doc("meta").get().then(function (m) {
      if (!m.exists) return null;
      var meta = m.data(), ids = ["app", "culture"];
      for (var i = 1; i <= meta.parts; i++) ids.push("entreprises-" + String(i).padStart(2, "0"));
      return Promise.all(ids.map(function (id) { return fs.collection("donnees").doc(id).get(); })).then(function (docs) {
        var app = docs[0].exists ? docs[0].data().html : null, culture = docs[1].exists ? JSON.parse(docs[1].data().json) : null, ent = [];
        for (var j = 2; j < docs.length; j++) { if (!docs[j].exists) return null; ent = ent.concat(JSON.parse(docs[j].data().json)); }
        if (!app || ent.length !== meta.total) return null;
        return { meta: meta, app: app, culture: culture, entreprises: ent };
      });
    });
  }
  function ecrireDonnees(app, entreprises, culture) {
    var parts = Math.ceil(entreprises.length / TAILLE), col = fs.collection("donnees"), q = Promise.resolve(), u = auth.currentUser;
    var tache = function (id, data) { q = q.then(function () { return col.doc(id).set(data); }); };
    tache("app", { html: app });
    tache("culture", { json: JSON.stringify(culture || { prospects: [] }) });
    for (var i = 0; i < parts; i++) tache("entreprises-" + String(i + 1).padStart(2, "0"), { json: JSON.stringify(entreprises.slice(i * TAILLE, (i + 1) * TAILLE)) });
    tache("meta", { parts: parts, total: entreprises.length, maj: new Date().toISOString(), par: (u && u.email) || "" });   // en dernier : une version incomplète n'est jamais lue
    return q;
  }

  /* ---------- Ouverture du CRM : la page du CRM remplace l'écran de connexion ---------- */
  var RESET = ":root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px/1.45 system-ui,-apple-system,'Segoe UI',sans-serif}img{max-width:100%}[hidden]{display:none!important}";
  function ouvrirCRM(d) {
    var origFetch = window.fetch.bind(window);
    window.fetch = function (u, o) {
      var s = String(u && u.url || u);
      if (/(^|\/)companies\.json(\?|$)/.test(s)) return Promise.resolve(new Response(JSON.stringify(d.entreprises), { headers: { "Content-Type": "application/json" } }));
      if (/(^|\/)culture\.json(\?|$)/.test(s)) return Promise.resolve(d.culture ? new Response(JSON.stringify(d.culture), { headers: { "Content-Type": "application/json" } }) : new Response("", { status: 404 }));
      return origFetch(u, o);
    };
    window.claude = { use: function (name) { return Promise.resolve(name === "db" ? dbShim : name === "user" ? userShim : null); } };
    var html = "<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\"><style>" + RESET + "</style></head><body>" + d.app + "</body></html>";
    document.open(); document.write(html); document.close();
    ajouterCompte();
  }
  function ajouterCompte() {   // « Déconnexion » et « Mettre à jour le CRM » à côté du témoin de synchronisation
    var box = document.querySelector(".top-actions") || document.body, u = auth.currentUser;
    var w = document.createElement("span");
    w.className = "compte";
    w.innerHTML = "<button type=\"button\" class=\"tbtn\" id=\"crmMaj\" title=\"Recharger les fichiers du CRM (après une mise à jour)\">Mettre à jour</button><button type=\"button\" class=\"tbtn\" id=\"crmOut\">Déconnexion</button>";
    w.style.cssText = "display:inline-flex;gap:10px;margin-left:12px;align-items:center;font-size:12.5px";
    box.appendChild(w);
    if (u) w.title = "Connecté : " + (u.email || "");
    document.getElementById("crmOut").addEventListener("click", function () { auth.signOut().then(function () { location.replace(location.pathname); }); });
    document.getElementById("crmMaj").addEventListener("click", function () { location.replace(location.pathname + "#maj-donnees"); location.reload(); });
  }

  /* ---------- Écran de connexion ---------- */
  var majDemandee = location.hash === "#maj-donnees";
  function membre(u) {   // fiche de l'associé (nom affiché dans l'équipe)
    return fs.collection("membres").doc(u.uid).set({ nom: u.displayName || (u.email || "").split("@")[0], email: u.email || "", vu: FV.serverTimestamp() }, { merge: true });
  }
  function apresConnexion(u) {
    if (!u.emailVerified) {
      show("#gLogin"); say("Adresse e-mail non vérifiée : un lien de vérification vient d'être envoyé à " + u.email + ". Clique dessus, puis reconnecte-toi.", "warn");
      u.sendEmailVerification().catch(function () {}).then(function () { return auth.signOut(); });
      return;
    }
    show("#gWait"); $("#gWaitTxt").textContent = "Chargement du CRM…";
    membre(u).then(function () {
      if (majDemandee) { history.replaceState(null, "", location.pathname); show("#gUpload"); $("#gUpTitle").textContent = "Mettre à jour le CRM"; return; }
      return lireDonnees().then(function (d) {
        if (d) ouvrirCRM(d);
        else { show("#gUpload"); $("#gUpTitle").textContent = "Première installation : charger le CRM"; }
      });
    }).catch(function (e) {
      if (e && e.code === "permission-denied") { show("#gDenied"); $("#gDeniedTxt").textContent = "Le compte " + (u.email || "") + " n'est pas autorisé. Demande à l'administrateur d'ajouter cette adresse dans les règles Firestore (voir le guide d'installation)."; }
      else { show("#gWait"); $("#gWaitTxt").textContent = "Connexion impossible pour le moment (" + ((e && e.code) || "erreur") + "). Recharge la page."; }
    });
  }
  var vu = false;
  auth.onAuthStateChanged(function (u) {
    if (u) { if (!vu) { vu = true; apresConnexion(u); } }
    else { vu = false; show("#gLogin"); }
  });
  $("#gGoogle").addEventListener("click", function () {
    say("");
    var p = new firebase.auth.GoogleAuthProvider();
    p.setCustomParameters({ prompt: "select_account" });
    auth.signInWithPopup(p).catch(function (e) {
      if (e && (e.code === "auth/popup-blocked" || e.code === "auth/operation-not-supported-in-this-environment")) return auth.signInWithRedirect(p);
      if (e && e.code !== "auth/popup-closed-by-user" && e.code !== "auth/cancelled-popup-request") say("Connexion Google impossible (" + e.code + ").", "warn");
    });
  });
  $("#gForm").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var em = $("#gEmail").value.trim(), pw = $("#gPass").value;
    if (!em || !pw) { say("Saisis l'adresse e-mail et le mot de passe.", "warn"); return; }
    say("Connexion…");
    auth.signInWithEmailAndPassword(em, pw).catch(function (e) {
      say(e && (e.code === "auth/wrong-password" || e.code === "auth/user-not-found" || e.code === "auth/invalid-credential" || e.code === "auth/invalid-login-credentials") ? "Adresse ou mot de passe incorrect." : "Connexion impossible (" + ((e && e.code) || "erreur") + ").", "warn");
    });
  });
  $("#gReset").addEventListener("click", function () {
    var em = $("#gEmail").value.trim();
    if (!em) { say("Saisis d'abord ton adresse e-mail.", "warn"); return; }
    auth.sendPasswordResetEmail(em).then(function () { say("Si ce compte existe, un e-mail de réinitialisation vient d'être envoyé.", "ok"); }, function () { say("Envoi impossible pour le moment.", "warn"); });
  });
  $("#gDeniedOut").addEventListener("click", function () { auth.signOut(); });

  /* ---------- Chargement des fichiers du CRM (installation et mises à jour) ---------- */
  var fichiers = {};
  function lireFichier(f) { return new Promise(function (ok, ko) { var r = new FileReader(); r.onload = function () { ok(String(r.result || "")); }; r.onerror = function () { ko(r.error); }; r.readAsText(f, "utf-8"); }); }
  $("#gFiles").addEventListener("change", function (ev) {
    var l = Array.prototype.slice.call(ev.target.files || []);
    Promise.all(l.map(function (f) { return lireFichier(f).then(function (t) { return [f.name, t]; }); })).then(function (paires) {
      paires.forEach(function (p) {
        var n = p[0].toLowerCase(), t = p[1];
        if (/\.html?$/.test(n)) fichiers.app = t;
        else if (/companies.*\.json$/.test(n)) fichiers.entreprises = t;
        else if (/culture.*\.json$/.test(n)) fichiers.culture = t;
      });
      majEtat();
    });
  });
  function verifier() {
    var e = [], ent = null, cul = null;
    if (!fichiers.app || !/id="viewAppels"/.test(fichiers.app) || !/function renderAppels/.test(fichiers.app)) e.push("index.html du CRM (dossier site)");
    try { ent = JSON.parse(fichiers.entreprises || ""); if (!Array.isArray(ent) || !ent.length || !ent[0].siren) { ent = null; throw 0; } } catch (x) { e.push("companies.json (dossier site)"); }
    try { cul = fichiers.culture ? JSON.parse(fichiers.culture) : null; } catch (x) { e.push("culture.json valide"); }
    return { manque: e, ent: ent, cul: cul };
  }
  function majEtat() {
    var v = verifier(), b = $("#gSend");
    $("#gFilesTxt").textContent = v.manque.length ? "Manque : " + v.manque.join(", ") + "." : "Prêt : CRM, " + v.ent.length + " entreprises" + (v.cul ? ", " + (v.cul.prospects || []).length + " prospects culture" : "") + ".";
    b.disabled = !!v.manque.length;
  }
  $("#gSend").addEventListener("click", function () {
    var v = verifier(), b = $("#gSend");
    if (v.manque.length) return;
    b.disabled = true; b.textContent = "Envoi…";
    ecrireDonnees(fichiers.app, v.ent, v.cul).then(function () { location.replace(location.pathname); }, function (e) {
      b.disabled = false; b.textContent = "Charger dans le CRM";
      $("#gFilesTxt").textContent = "Envoi impossible (" + ((e && e.code) || "erreur") + ").";
    });
  });
  $("#gUpCancel").addEventListener("click", function () { location.replace(location.pathname); });
})();
