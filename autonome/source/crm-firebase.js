/* CRM Entreprises Nièvre, version autonome (sans claude.ai) : connexion Google, données et suivi dans Firestore.
   La page publique ne contient que cet écran de connexion. Après connexion d'un associé autorisé (règles Firestore), le CRM
   (donnees/app), les fiches (donnees/entreprises-NN), les prospects culture (donnees/culture) et l'étude Hermes360
   (donnees/etude) sont lus dans Firestore, puis la page du CRM est écrite à la place de celle-ci. Le CRM y trouve
   window.claude.use("db") et use("user") avec la même interface que sur claude.ai : son code est le même dans les deux versions.
   Seul le propriétaire (règles Firestore) peut charger une nouvelle version du CRM ou des données. */
(function () {
  "use strict";
  var CFG = window.CRM_CONFIG || {};
  var $ = function (s) { return document.querySelector(s); };
  var msg = $("#gmsg");
  function say(t, kind) { if (!msg) return; msg.textContent = t || ""; msg.className = "gmsg" + (kind ? " " + kind : ""); }
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

  /* ---------- Base partagée : même interface que claude.ai (collection, doc, get, set, update fusionnant, onSnapshot) ---------- */
  var isObj = function (v) { return v && typeof v === "object" && !Array.isArray(v); };
  // Firestore refuse un tableau dans un tableau (réglages Hermes360 : [[clé, valeur], …]) : stocké { __a: […] }, relu tel quel
  function enc(v, dansTableau) {
    if (Array.isArray(v)) { var a = v.map(function (x) { return enc(x, true); }); return dansTableau ? { __a: a } : a; }
    if (isObj(v)) { var o = {}; Object.keys(v).forEach(function (k) { o[k] = enc(v[k]); }); return o; }
    return v;
  }
  function dec(v) {
    if (Array.isArray(v)) return v.map(dec);
    if (!isObj(v) || Object.getPrototypeOf(v) !== Object.prototype) return v;
    var ks = Object.keys(v); if (ks.length === 1 && ks[0] === "__a" && Array.isArray(v.__a)) return dec(v.__a);
    var o = {}; ks.forEach(function (k) { o[k] = dec(v[k]); }); return o;
  }
  function flatten(o, pre, out) {   // { journal: { id1: {...} } } -> chemin journal.id1 ; null -> champ supprimé ; {} -> rien
    Object.keys(o).forEach(function (k) {
      var v = o[k], p = pre.concat([k]);
      if (v === undefined) return;
      if (isObj(v)) { if (Object.keys(v).length) flatten(v, p, out); }
      else out.push(new FP(...p), v === null ? FV.delete() : enc(v));
    });
    return out;
  }
  function fusion(o) {   // set() fusionnant : deux associés qui créent la même fiche en même temps ne s'écrasent pas
    var r = {};
    Object.keys(o).forEach(function (k) { var v = o[k]; if (v === undefined) return; if (v === null) r[k] = FV.delete(); else if (isObj(v)) { if (Object.keys(v).length) r[k] = fusion(v); } else r[k] = enc(v); });
    return r;
  }
  function err(e) { var c = e && e.code, x = new Error((e && e.message) || String(e)); x.code = c === "not-found" ? "invalid_argument" : c === "permission-denied" ? "permission_denied" : c === "failed-precondition" || c === "aborted" || c === "deadline-exceeded" ? "unavailable" : c; return x; }
  function wrapSnap(d) { return { id: d.id, exists: d.exists, data: function () { return dec(d.data()); } }; }
  // Écriture par transaction sans lecture : envoyée au serveur, jamais mise en file hors ligne (comme sur claude.ai, une
  // écriture sans réseau échoue et le CRM propose « Réessayer »).
  function ecrire(f) { return fs.runTransaction(function (t) { f(t); return Promise.resolve(); }).catch(function (e) { throw err(e); }); }
  function docRef(col, id) {
    var r = fs.collection(col).doc(id);
    return {
      get: function () { return r.get().then(wrapSnap, function (e) { throw err(e); }); },
      set: function (v) { var d = fusion(v); return ecrire(function (t) { t.set(r, d, { merge: true }); }); },
      update: function (v) { var a = flatten(v, [], []); if (!a.length) return Promise.resolve(); return ecrire(function (t) { t.update.apply(t, [r].concat(a)); }); },
      delete: function () { return ecrire(function (t) { t.delete(r); }); }
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

  /* ---------- Données du CRM dans Firestore (écrites d'un seul lot, document par document sous 900 Ko) ---------- */
  var MAXO = 900000, octets = function (s) { return new TextEncoder().encode(s).length; };
  function decouper(ent) {
    var parts = [], cur = [], n = 2;
    ent.forEach(function (e) { var o = octets(JSON.stringify(e)) + 1; if (cur.length && n + o > MAXO) { parts.push(cur); cur = []; n = 2; } cur.push(e); n += o; });
    if (cur.length) parts.push(cur);
    return parts;
  }
  function lireDonnees() {
    return fs.collection("donnees").doc("meta").get().then(function (m) {
      if (!m.exists) return null;
      var meta = m.data(), ids = ["app", "culture", "etude"];
      for (var i = 1; i <= meta.parts; i++) ids.push("entreprises-" + String(i).padStart(2, "0"));
      return Promise.all(ids.map(function (id) { return fs.collection("donnees").doc(id).get(); })).then(function (docs) {
        var dd = docs.map(function (d) { return d.exists ? d.data() : null; });
        if (!dd[0] || dd[0].v !== meta.v) return null;
        var ent = [];
        for (var j = 3; j < dd.length; j++) { if (!dd[j] || dd[j].v !== meta.v) return null; ent = ent.concat(JSON.parse(dd[j].json)); }
        if (ent.length !== meta.total) return null;
        return { meta: meta, app: dd[0].html, culture: dd[1] ? JSON.parse(dd[1].json) : null, etude: dd[2] ? dd[2].html : null, entreprises: ent };
      });
    });
  }
  function ecrireDonnees(app, entreprises, culture, etude) {
    var v = Date.now().toString(36), col = fs.collection("donnees"), u = auth.currentUser, b = fs.batch();
    var docs = [["app", { html: app, v: v }]];
    if (culture) docs.push(["culture", { json: JSON.stringify(culture), v: v }]);   // non choisi : prospects actuels conservés
    if (etude) docs.push(["etude", { html: etude, v: v }]);
    var parts = decouper(entreprises);
    parts.forEach(function (p, i) { docs.push(["entreprises-" + String(i + 1).padStart(2, "0"), { json: JSON.stringify(p), v: v }]); });
    for (var i = 0; i < docs.length; i++) { var o = octets(docs[i][1].html || docs[i][1].json); if (o > MAXO) return Promise.reject({ code: "fichier trop gros (" + docs[i][0] + ")" }); }
    docs.forEach(function (d) { b.set(col.doc(d[0]), d[1]); });
    b.set(col.doc("meta"), { v: v, parts: parts.length, total: entreprises.length, maj: new Date().toISOString(), par: (u && u.email) || "" });
    return b.commit();   // un seul lot : jamais une version à moitié écrite
  }

  /* ---------- Ouverture du CRM : la page du CRM remplace l'écran de connexion ---------- */
  var RESET = ":root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px/1.45 system-ui,-apple-system,'Segoe UI',sans-serif}img{max-width:100%}[hidden]{display:none!important}";
  var ouvertPour = null;   // associé pour qui le CRM est affiché
  function ouvrirCRM(d) {
    ouvertPour = auth.currentUser && auth.currentUser.uid;
    var origFetch = window.fetch.bind(window);
    window.fetch = function (u, o) {
      var s = String(u && u.url || u);
      if (/(^|\/)companies\.json(\?|$)/.test(s)) return Promise.resolve(new Response(JSON.stringify(d.entreprises), { headers: { "Content-Type": "application/json" } }));
      if (/(^|\/)culture\.json(\?|$)/.test(s)) return Promise.resolve(d.culture ? new Response(JSON.stringify(d.culture), { headers: { "Content-Type": "application/json" } }) : new Response("", { status: 404 }));
      return origFetch(u, o);
    };
    if (d.etude) window.CRM_ETUDE = URL.createObjectURL(new Blob(["<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><style>" + RESET + "</style></head><body>" + d.etude + "</body></html>"], { type: "text/html" }));
    window.claude = { use: function (name) { return Promise.resolve(name === "db" ? dbShim : name === "user" ? userShim : null); } };
    var html = "<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\"><style>" + RESET + "</style></head><body>" + d.app + "</body></html>";
    document.open(); document.write(html); document.close();
    // document.open() retire les écouteurs « online » de Firestore : sans ceci, le suivi ne se resynchronise pas après une coupure
    window.addEventListener("online", function () { fs.disableNetwork().then(function () { return fs.enableNetwork(); }); });
    ajouterCompte();
  }
  function ajouterCompte() {   // « Déconnexion » et « Mettre à jour » à côté du témoin de synchronisation
    var box = document.querySelector(".top-actions") || document.body, u = auth.currentUser;
    var w = document.createElement("span");
    w.className = "compte";
    w.innerHTML = "<button type=\"button\" class=\"tbtn\" id=\"crmMaj\" title=\"Charger une nouvelle version du CRM (réservé au propriétaire)\">Mettre à jour</button><button type=\"button\" class=\"tbtn\" id=\"crmOut\">Déconnexion</button>";
    w.style.cssText = "display:inline-flex;gap:10px;margin-left:12px;align-items:center;font-size:12.5px";
    box.appendChild(w);
    if (u) w.title = "Connecté : " + (u.email || "");
    var boutons = w.querySelectorAll("button");
    function quitter(b, suite) {   // la saisie en cours est enregistrée avant de quitter la page
      var a = document.activeElement; if (a && a !== document.body && a.blur) a.blur();   // sortie du champ : le CRM enregistre
      Array.prototype.forEach.call(boutons, function (x) { x.disabled = true; }); b.textContent = "Enregistrement…";
      setTimeout(function () {
        var c = typeof chains === "object" && chains ? Object.keys(chains).map(function (k) { return chains[k]; }) : [];   // écritures du CRM en cours
        var fini = Promise.all(c.map(function (p) { return Promise.resolve(p).catch(function () {}); })).then(function () { return true; });
        Promise.race([fini, new Promise(function (ok) { setTimeout(function () { ok(false); }, 15000); })]).then(function (ok) {
          if (ok || confirm("Des modifications ne sont pas encore enregistrées (connexion lente ou coupée). Quitter quand même et les perdre ?")) return suite();
          Array.prototype.forEach.call(boutons, function (x) { x.disabled = false; }); b.textContent = b.id === "crmOut" ? "Déconnexion" : "Mettre à jour";
        });
      }, 50);
    }
    document.getElementById("crmOut").addEventListener("click", function () { quitter(this, function () { ouvertPour = null; auth.signOut().then(function () { location.replace(location.pathname); }); }); });
    document.getElementById("crmMaj").addEventListener("click", function () { quitter(this, function () { location.replace(location.pathname + "#maj-donnees"); location.reload(); }); });
  }

  /* ---------- Écran de connexion (Google seulement) ---------- */
  var majDemandee = location.hash === "#maj-donnees";
  function membre(u) {   // fiche de l'associé (nom affiché dans l'équipe)
    return fs.collection("membres").doc(u.uid).set({ nom: u.displayName || (u.email || "").split("@")[0], email: u.email || "", vu: FV.serverTimestamp() }, { merge: true });
  }
  function refus(u) { show("#gDenied"); $("#gDeniedTxt").textContent = "Le compte " + (u.email || "") + " n'est pas autorisé. Demande à l'administrateur d'ajouter cette adresse dans les règles du CRM (voir le guide d'installation)."; }
  function apresConnexion(u) {
    show("#gWait"); $("#gWaitTxt").textContent = "Chargement du CRM…";
    membre(u).then(function () {
      if (majDemandee) { history.replaceState(null, "", location.pathname); show("#gUpload"); $("#gUpTitle").textContent = "Mettre à jour le CRM"; return; }
      return lireDonnees().then(function (d) {
        if (d) ouvrirCRM(d);
        else { show("#gUpload"); $("#gUpTitle").textContent = "Première installation : charger le CRM"; }
      });
    }).catch(function (e) {
      if (e && e.code === "permission-denied") refus(u);
      else { show("#gWait"); $("#gWaitTxt").textContent = "Connexion impossible pour le moment (" + ((e && e.code) || "erreur") + "). Recharge la page."; }
    });
  }
  var vu = false;
  auth.onAuthStateChanged(function (u) {
    if (ouvertPour && (!u || u.uid !== ouvertPour)) { location.replace(location.pathname); return; }   // déconnexion ou autre compte (autre onglet) : vider la page
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
  $("#gDeniedOut").addEventListener("click", function () { auth.signOut(); });

  /* ---------- Chargement des fichiers du CRM (installation et mises à jour, propriétaire seulement) ---------- */
  var fichiers = {};
  function lireFichier(f) { return new Promise(function (ok, ko) { var r = new FileReader(); r.onload = function () { ok(String(r.result || "")); }; r.onerror = function () { ko(r.error); }; r.readAsText(f, "utf-8"); }); }
  $("#gFiles").addEventListener("change", function (ev) {
    var l = Array.prototype.slice.call(ev.target.files || []);
    Promise.all(l.map(function (f) { return lireFichier(f).then(function (t) { return [f.name, t]; }); })).then(function (paires) {
      paires.forEach(function (p) {
        var n = p[0].toLowerCase(), t = p[1];
        if (/hermes.*\.html?$/.test(n)) fichiers.etude = t;
        else if (/\.html?$/.test(n)) fichiers.app = t;
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
    try { cul = fichiers.culture ? JSON.parse(fichiers.culture) : null; if (cul && !Array.isArray(cul.prospects)) { cul = null; throw 0; } } catch (x) { e.push("culture.json valide"); }
    return { manque: e, ent: ent, cul: cul };
  }
  function majEtat() {
    var v = verifier(), b = $("#gSend");
    $("#gFilesTxt").textContent = v.manque.length ? "Manque : " + v.manque.join(", ") + "." : "Prêt : CRM, " + v.ent.length + " entreprises"
      + (v.cul ? ", " + v.cul.prospects.length + " prospects culture" : " (culture.json non choisi : prospects actuels conservés)")
      + (fichiers.etude ? ", étude Hermes360" : "") + ".";
    b.disabled = !!v.manque.length;
  }
  $("#gSend").addEventListener("click", function () {
    var v = verifier(), b = $("#gSend");
    if (v.manque.length) return;
    b.disabled = true; b.textContent = "Envoi…";
    ecrireDonnees(fichiers.app, v.ent, v.cul, fichiers.etude).then(function () { location.replace(location.pathname); }, function (e) {
      b.disabled = false; b.textContent = "Charger dans le CRM";
      $("#gFilesTxt").textContent = e && e.code === "permission-denied" ? "Seul le propriétaire du CRM peut charger une nouvelle version (voir le guide d'installation)." : "Envoi impossible (" + ((e && e.code) || "erreur") + ").";
    });
  });
  $("#gUpCancel").addEventListener("click", function () { location.replace(location.pathname); });
})();
