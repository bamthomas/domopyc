$(document).ready(function () {
    Highcharts.setOptions({
        global: {
            useUTC: false
        }
    });

    function createChart(jsonData) {
        $('#chart').highcharts({
            chart: {
                zoomType: 'x'
            },
            title: {
                text: 'Consommation électrique'
            },
            subtitle: {
                text: document.ontouchstart === undefined ?
                    'sélectionner une zone dans le graph pour zoomer' :
                    'Pinch the chart to zoom in'
            },
            xAxis: {
                type: 'datetime',
                minRange: 24 * 3600000 // one day
            },
            yAxis: {
                title: {
                    text: 'puissance (kWh)'
                },
                min : 0
            },
            legend: {
                enabled: false
            },
            plotOptions: {
                area: {
                    fillColor: {
                        linearGradient: {x1: 0, y1: 0, x2: 0, y2: 1},
                        stops: [
                            [0, Highcharts.getOptions().colors[0]],
                            [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]
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
            series: [{
                type: 'area',
                name: 'Consommation',
                data: jsonData
            }]
        });
    }

    $.getJSON('/power/history', function (data) {
        var dataWithDates = [];
        _(data.data).forEach(function(point) {
            dataWithDates.push([Date.parse(point[0]), point[1]]);
        });
        createChart(dataWithDates);
    });
});