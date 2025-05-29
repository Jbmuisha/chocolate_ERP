document.addEventListener('DOMContentLoaded', () => {
    // Global chart variables
    let salesTrendChart, dailyProductChart, weeklyProductChart, monthlyProductChart, yearlyProductChart;

    // Helper: create a chart instance on given canvas with label and initial data
    function createBarChart(canvasId, labelName = 'Units Sold', labels = [], data = []) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        return new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: labelName,
                    data: data,
                    backgroundColor: 'rgba(59, 130, 246, 0.7)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 1,
                    borderRadius: 6,
                    maxBarThickness: 35
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: labelName !== '' },
                    tooltip: { enabled: true }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }

    // Initialize charts using data embedded in data attributes on canvas elements
    function initCharts() {
        function getCanvasData(id) {
            const c = document.getElementById(id);
            if (!c) return {labels: [], data: []};
            try {
                return {
                    labels: JSON.parse(c.dataset.labels),
                    data: JSON.parse(c.dataset.data)
                };
            } catch {
                return {labels: [], data: []};
            }
        }

        let d = getCanvasData('salesTrendChart');
        salesTrendChart = createBarChart('salesTrendChart', 'Total Units Sold', d.labels, d.data);

        d = getCanvasData('dailyProductChart');
        dailyProductChart = createBarChart('dailyProductChart', 'Daily Units Sold', d.labels, d.data);

        d = getCanvasData('weeklyProductChart');
        weeklyProductChart = createBarChart('weeklyProductChart', 'Weekly Units Sold', d.labels, d.data);

        d = getCanvasData('monthlyProductChart');
        monthlyProductChart = createBarChart('monthlyProductChart', 'Monthly Units Sold', d.labels, d.data);

        const yearlyCanvas = document.getElementById('yearlyProductChart');
        if (yearlyCanvas) {
            d = getCanvasData('yearlyProductChart');
            yearlyProductChart = createBarChart('yearlyProductChart', 'Yearly Units Sold', d.labels, d.data);
        }
    }

    // Call init on page load
    initCharts();

    // Function to update chart data and redraw
    function updateChart(chart, labels, data) {
        if (!chart) return;
        chart.data.labels = labels;
        chart.data.datasets[0].data = data;
        chart.update();
    }

    // Update the sales summary cards by ID and new value
    function updateSummaryCard(id, value) {
        const card = document.getElementById(id);
        if (card) {
            card.querySelector('p').textContent = `${value} units`;
        }
    }

    // Helper to update sales list container with new sales items
    function updateSalesList(containerId, sales, emptyMessage) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (sales.length === 0) {
            container.innerHTML = `<li class="py-3 text-center text-gray-400">${emptyMessage}</li>`;
            return;
        }

        container.innerHTML = sales.map(sale => `
            <li class="py-3 flex justify-between">
                <span>${sale.product} (${sale.quantity} units)</span>
                <span class="text-gray-400">${sale.sale_date}</span>
            </li>
        `).join('');
    }

    // Fetch updated data from backend and update charts and UI
    async function fetchAndUpdateDashboard() {
        try {
            const response = await fetch('/api/dashboard_data');
            if (!response.ok) throw new Error('Network response not OK');

            const data = await response.json();

            // Update summary cards
            updateSummaryCard('dailySalesCard', data.daily_total);
            updateSummaryCard('weeklySalesCard', data.weekly_total);
            if (data.monthly_total !== undefined) updateSummaryCard('monthlySalesCard', data.monthly_total);
            if (data.yearly_total !== undefined) updateSummaryCard('yearlySalesCard', data.yearly_total);

            // Update charts
            updateChart(salesTrendChart, data.labels, data.data);
            updateChart(dailyProductChart, data.daily_labels, data.daily_data);
            updateChart(weeklyProductChart, data.weekly_labels, data.weekly_data);
            updateChart(monthlyProductChart, data.monthly_labels, data.monthly_data);
            if (yearlyProductChart && data.yearly_labels && data.yearly_data) {
                updateChart(yearlyProductChart, data.yearly_labels, data.yearly_data);
            }

            // Update sales breakdown lists
            updateSalesList('dailySalesList', data.daily_sales, 'No sales today.');
            updateSalesList('weeklySalesList', data.weekly_sales, 'No sales this week.');
            if (data.monthly_sales !== undefined) {
                updateSalesList('monthlySalesList', data.monthly_sales, 'No sales this month.');
            }
            if (data.yearly_sales !== undefined) {
                updateSalesList('yearlySalesList', data.yearly_sales, 'No sales this year.');
            }

        } catch (err) {
            console.error('Error fetching or updating dashboard data:', err);
        }
    }

    // Initial fetch
    fetchAndUpdateDashboard();

    // Fetch every 30 seconds
    setInterval(fetchAndUpdateDashboard, 30000);

    // Sidebar toggle code (your existing)
    document.getElementById("toggleSidebar").addEventListener("click", function () {
        const sidebar = document.getElementById("sidebar");
        sidebar.classList.toggle("hidden");
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const addItemBtn = document.getElementById('add-item-btn');
    const orderItemsDiv = document.getElementById('order-items');
  
    addItemBtn.addEventListener('click', () => {
      // Clone the first order item row
      const firstItem = orderItemsDiv.querySelector('div.flex');
      const newItem = firstItem.cloneNode(true);
  
      // Reset inputs in the cloned row
      const selects = newItem.querySelectorAll('select');
      selects.forEach(select => {
        select.selectedIndex = 0; // Reset to default (Select Product)
      });
  
      const inputs = newItem.querySelectorAll('input');
      inputs.forEach(input => {
        input.value = '';
      });
  
      orderItemsDiv.appendChild(newItem);
  
      attachRemoveListeners(); // Reattach remove event listeners
    });
  
    function attachRemoveListeners() {
      const removeButtons = orderItemsDiv.querySelectorAll('.remove-item-btn');
  
      removeButtons.forEach(btn => {
        btn.onclick = (e) => {
          const allItems = orderItemsDiv.querySelectorAll('div.flex');
          if (allItems.length > 1) {
            e.target.closest('div.flex').remove();
          } else {
            alert('At least one order item is required.');
          }
        };
      });
    }
  
    attachRemoveListeners();
  });
  
