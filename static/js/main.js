// Sidebar mobile
const hamburger = document.getElementById('hamburger');
const sidebar   = document.getElementById('sidebar');
const overlay   = document.getElementById('overlay');
const sidebarClose = document.getElementById('sidebarClose');

function ouvrirSidebar() {
    sidebar.classList.add('open');
    overlay.classList.add('open');
}

function fermerSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('open');
}

if (hamburger) hamburger.addEventListener('click', ouvrirSidebar);
if (sidebarClose) sidebarClose.addEventListener('click', fermerSidebar);
if (overlay) overlay.addEventListener('click', fermerSidebar);

// Fermer la sidebar quand on clique sur un lien
document.querySelectorAll('.sidebar nav a').forEach(link => {
    link.addEventListener('click', fermerSidebar);
});