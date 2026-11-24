// Stand-in for JATOS's jatos.js, used only by tests/run_flow.py --jatos.
// Records what the experiment would send to the server.
window.__jatosLog = { appended: [], files: {}, ended: null };
window.jatos = {
  urlQueryParameters: Object.fromEntries(new URLSearchParams(location.search)),
  onLoad: (f) => window.addEventListener("load", f),
  appendResultData: (s) => { window.__jatosLog.appended.push(s); return Promise.resolve(); },
  uploadResultFile: (s, name) => { window.__jatosLog.files[name] = s; return Promise.resolve(); },
  endStudyAndRedirect: (url, ok, msg) => {
    window.__jatosLog.ended = { url, ok, msg };
    document.body.innerHTML = "<p>JATOS mock: study ended</p>";
  },
};
