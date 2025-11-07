(function () {
    const overlay = document.createElement('div');
    overlay.id = 'loader-overlay';
    overlay.innerHTML = `
        <img id="loader-logo" src="/assets/favicon.ico" alt="Logo">
        <div id="loader-text">Bienvenue dans le laboratoire</div>
    `;

    document.addEventListener('DOMContentLoaded', function () {
        document.body.appendChild(overlay);
    });

    // Quand tout est prêt, on attend encore un peu avant de retirer le loader
    window.addEventListener('load', function () {
        const loader = document.getElementById('loader-overlay');
        if (!loader) return;

        // ⏱ délai en millisecondes
        const DELAY = 2000; // = 2 secondes
        setTimeout(() => {
            loader.classList.add('fade-out');
            setTimeout(() => loader.remove(), 450);
        }, DELAY);
    });
})();