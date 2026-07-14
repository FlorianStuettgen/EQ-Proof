'use strict';

(() => {
  const isStaticShowcase = window.location.hostname.endsWith('.github.io')
    || window.location.port === '4173';
  if (!isStaticShowcase) return;

  const nativeFetch = window.fetch.bind(window);
  window.fetch = (input, options = {}) => {
    const requestUrl = new URL(
      typeof input === 'string' || input instanceof URL ? input : input.url,
      window.location.href,
    );
    const path = requestUrl.pathname.replace(/\/+$/, '');

    if (path.endsWith('/api/health')) {
      return Promise.resolve(new Response(
        JSON.stringify({ detail: 'Static showcase mode' }),
        {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        },
      ));
    }

    if (path.endsWith('/api/demo')) {
      return nativeFetch(new URL('./demo-data.json', window.location.href), options);
    }

    if (path.endsWith('/api/catalogue')) {
      return nativeFetch(new URL('./demo-data.json', window.location.href), options)
        .then(async (response) => {
          if (!response.ok) return response;
          const payload = await response.json();
          return new Response(JSON.stringify(payload.catalogue || []), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          });
        });
    }

    return nativeFetch(input, options);
  };
})();
