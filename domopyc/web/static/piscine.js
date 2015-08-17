var chart;

$(document).ready(function () {
    Highcharts.setOptions({
        global: {
            useUTC: false
        }
    });

    chart = new Highcharts.Chart({
        chart: {
            renderTo: 'chart',
            type: 'areaspline',
            marginRight: 10
        },
        title: {
            text: 'Température de la piscine'
        },
        xAxis: {
            type: 'datetime',
            tickPixelInterval: 150
        },
        yAxis: {
            title: {
                text: '°C'
            }
        },
        legend: {
            enabled: false
        },
        exporting: {
            enabled: false
        },
        series: [
            {
                name: 'Température piscine',
                data: POOL_TEMPERATURES
            }
        ]
    });
});
