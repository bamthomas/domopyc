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
        plotOptions: {
            area: {
                fillColor: {
                    linearGradient: {x1: 0, y1: 0, x2: 0, y2: 1},
                    stops: [
                        [0,'#DF7514'],
                        [1, 'white']
                    ]
                },
                marker: {
                    radius: 2
                },
                lineWidth: 1,
                states: {
                    hover: {
                        lineWidth: 1
                    }
                },
                threshold: null
            }
        },
        legend: {
            enabled: false
        },
        series: [
            {
                type: 'area',
                name: 'Température piscine',
                data: POOL_TEMPERATURES,
                color: '#DF7514'
            }
        ]
    });
});
