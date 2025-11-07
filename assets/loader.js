(function () {
    // Crée l'overlay au chargement du document
    const overlay = document.createElement('div');
    overlay.id = 'loader-overlay';

    overlay.innerHTML = `
        <img id="loader-logo" src="/assets/favicon.ico" alt="Logo">
        <div id="loader-text">Bienvenue dans le laboratoire</div>
    `;

    document.addEventListener('DOMContentLoaded', function () {
        document.body.appendChild(overlay);
    });

    // Quand tout est prêt, on masque le loader
    window.addEventListener('load', function () {
        const loader = document.getElementById('loader-overlay');
        if (!loader) return;
        loader.classList.add('fade-out');
        setTimeout(() => loader.remove(), 450);
    });
})();