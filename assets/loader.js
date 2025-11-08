(function () {
    // Crée l'overlay
    const overlay = document.createElement('div');
    overlay.id = 'loader-overlay';
    overlay.innerHTML = `
        <img id="loader-logo" src="/assets/favicon.ico" alt="Logo">
        <div id="loader-text">Bienvenue dans le laboratoire</div>
        <div id="loader-subtext">Chargement des visualisations...</div>
    `;

    // Ajoute l'overlay au DOM dès que le HTML est prêt
    document.addEventListener('DOMContentLoaded', function () {
        document.body.appendChild(overlay);
    });

    // Fonction pour masquer le loader avec un petit fondu
    function hideLoader(delay = 500) {
        const loader = document.getElementById('loader-overlay');
        if (!loader) return;
        setTimeout(() => {
            loader.classList.add('fade-out');
            setTimeout(() => loader.remove(), 450);
        }, delay);
    }

    // Attend que Dash ait tout rendu
    document.addEventListener('dash-rendered', () => {
        hideLoader(1000); // 1s après rendu pour la fluidité
    });

    // Sécurité : fallback après 5s si dash-rendered ne se déclenche pas
    window.addEventListener('load', () => {
        setTimeout(() => {
            const loader = document.getElementById('loader-overlay');
            if (loader) hideLoader(0);
        }, 1000);
    });
})();
