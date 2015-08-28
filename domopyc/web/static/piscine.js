var chart;

$(document).ready(function () {
    Highcharts.setOptions({
        global: {
            useUTC: false
        }
    });

    chart = new Highcharts.Chart({
        chart: {
            zoomType: 'x',
            renderTo: 'chart'
        },
        title: {
            text: 'Température de la piscine'
        },
        xAxis: {
            type: 'datetime',
            minRange: 24 * 3600000
        },
        yAxis: {
            title: {
                text: '°C'
            }
        },
        legend: {
            enabled: false
        },
        series: [
            {
                name: 'Température piscine',
                data: POOL_TEMPERATURES,
                color: '#DF7514'
            }
        ]
    });
});
