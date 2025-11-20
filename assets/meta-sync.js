// Convertit meta name="og:*" en meta property="og:*" et met à jour canonical
(function(){
  try {
    var head = document.head || document.getElementsByTagName('head')[0];
    var metas = head.querySelectorAll('meta[name^="og:"]');
    metas.forEach(function(m){
      var prop = m.getAttribute('name');
      var content = m.getAttribute('content');
      var existing = head.querySelector('meta[property="'+prop+'"]');
      if (existing) {
        existing.setAttribute('content', content || '');
      } else {
        var n = document.createElement('meta');
        n.setAttribute('property', prop);
        if (content) n.setAttribute('content', content);
        head.appendChild(n);
      }
    });

    // Canonical depuis meta container dynamique
    var canonicalLink = head.querySelector('link[rel="canonical"]');
    if (!canonicalLink){
      canonicalLink = document.createElement('link');
      canonicalLink.setAttribute('rel','canonical');
      head.appendChild(canonicalLink);
    }
    var dyn = document.getElementById('dynamic-meta');
    if (dyn){
      var link = dyn.querySelector('link[rel="canonical"]');
      if (link){
        canonicalLink.setAttribute('href', link.getAttribute('href'));
      } else {
        // fallback local
        canonicalLink.setAttribute('href', window.location.origin + (window.location.pathname||'/'));
      }
    }
  } catch(e){}
})();