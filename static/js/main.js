// Main JavaScript file

// Function to toggle between light and dark themes
function initThemeToggle() {
  const themeToggleBtn = document.getElementById('theme-toggle');
  const htmlElement = document.documentElement;
  const lightIcon = document.querySelector('.theme-light');
  const darkIcon = document.querySelector('.theme-dark');
  
  // Check if theme preference is stored in localStorage
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme) {
    if (savedTheme === 'light') {
      htmlElement.classList.remove('dark');
      lightIcon.style.display = 'inline-block';
      darkIcon.style.display = 'none';
    } else {
      htmlElement.classList.add('dark');
      lightIcon.style.display = 'none';
      darkIcon.style.display = 'inline-block';
    }
  }

  // Toggle theme when button is clicked
  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', function() {
      if (htmlElement.classList.contains('dark')) {
        // Switch to light mode
        htmlElement.classList.remove('dark');
        lightIcon.style.display = 'inline-block';
        darkIcon.style.display = 'none';
        localStorage.setItem('theme', 'light');
      } else {
        // Switch to dark mode
        htmlElement.classList.add('dark');
        lightIcon.style.display = 'none';
        darkIcon.style.display = 'inline-block';
        localStorage.setItem('theme', 'dark');
      }
    });
  }
}

// Function to initialize datatables if they exist on the page
function initDataTables() {
  if (typeof jQuery !== 'undefined' && typeof jQuery.fn.DataTable !== 'undefined' && document.getElementById('results-table')) {
    jQuery('#results-table').DataTable({
      order: [[6, 'desc']], // Sort by CoC Return by default
      responsive: true,
      pageLength: 25,
      language: {
        search: "Filter results:"
      }
    });
  }
}

// Wait for the page to load then initialize components
document.addEventListener('DOMContentLoaded', function() {
  // Initialize theme toggle
  initThemeToggle();
  
  // Initialize datatables
  setTimeout(initDataTables, 100);
});