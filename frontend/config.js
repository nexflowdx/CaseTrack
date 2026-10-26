/* URLs de API do CaseTrack, em um só lugar.

   Segurança: produção só é usada quando a página é servida de um host da
   lista PRODUCTION_HOSTS. Qualquer outro host (localhost, IP, file://,
   homologação, domínio novo) usa URLs de desenvolvimento, então um teste
   nunca chama produção por acidente.

   Desenvolvimento: padrão http://localhost:8000 (backend) e
   http://localhost:8001 (Login API, caso exista uma local). Para apontar
   para outros serviços, defina no console do navegador:
     localStorage.setItem('casetrack_dev_api',
       JSON.stringify({ backendUrl: 'http://localhost:9000',
                        loginApiUrl: 'http://localhost:9001' }))
   O override é ignorado em produção e rejeitado se apontar para um host
   de produção. */
(function () {
  var PRODUCTION_HOSTS = ['nexflow-casetrack-frontend.tlwieg.easypanel.host'];

  var PRODUCTION = {
    loginApiUrl: 'https://api-login.nexflowdx.cloud',
    backendUrl: 'https://nexflow-casetrack-backend.tlwieg.easypanel.host'
  };

  var DEVELOPMENT = {
    loginApiUrl: 'http://localhost:8001',
    backendUrl: 'http://localhost:8000'
  };

  function hostOf(url) {
    try { return new URL(url).hostname; } catch (e) { return null; }
  }

  var productionApiHosts = [hostOf(PRODUCTION.loginApiUrl), hostOf(PRODUCTION.backendUrl)];

  function safeOverride(url) {
    var host = hostOf(url);
    if (!host || !/^https?:\/\//.test(url)) return null;
    if (productionApiHosts.indexOf(host) !== -1) return null;
    return url.replace(/\/+$/, '');
  }

  function devConfig() {
    var cfg = { loginApiUrl: DEVELOPMENT.loginApiUrl, backendUrl: DEVELOPMENT.backendUrl };
    try {
      var o = JSON.parse(localStorage.getItem('casetrack_dev_api') || 'null');
      if (o) {
        cfg.loginApiUrl = safeOverride(o.loginApiUrl) || cfg.loginApiUrl;
        cfg.backendUrl = safeOverride(o.backendUrl) || cfg.backendUrl;
      }
    } catch (e) { /* override inválido: mantém o padrão de desenvolvimento */ }
    return cfg;
  }

  var isProduction = PRODUCTION_HOSTS.indexOf(window.location.hostname) !== -1;

  window.CASETRACK_CONFIG = Object.freeze(
    Object.assign({ environment: isProduction ? 'production' : 'development' },
                  isProduction ? PRODUCTION : devConfig())
  );
})();
