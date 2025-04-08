function runAnomalyDetection() {
    const contamination = document.getElementById('contamination').value;

    fetch('/anomaly-detection/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: `contamination=${contamination}`
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok: ' + response.statusText);
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            alert('Error from server: ' + data.error);
            return;
        }
        if (!data.anomalies) {
            alert('No anomalies found or unexpected response format.');
            return;
        }
        const tbody = document.getElementById('anomaly-results');
        tbody.innerHTML = '';
        data.anomalies.forEach(anomaly => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${anomaly.transaction_id}</td>
                <td>${anomaly.item_name}</td>
                <td>${anomaly.unit_price}</td>
                <td>${anomaly.procurement_method}</td>
                <td>${anomaly.anomaly_score}</td>
            `;
            tbody.appendChild(row);
        });
    })
    .catch(error => {
        alert('Error running anomaly detection: ' + error.message);
    });
}