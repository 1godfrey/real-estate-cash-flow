// Main JavaScript file

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
  // Initialize datatables
  setTimeout(initDataTables, 100);
});