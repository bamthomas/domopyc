$(document).ready(function () {
    $('#history').on('click', function () {
        $.getJSON('/power/history', function (json) {
            var dataWithDates = [];
            _(json.data).forEach(function (point) {
                dataWithDates.push([Date.parse(point[0]), point[1]]);
            });
            createHistoryChart('#chart', dataWithDates);
        });
    });

    $('#by_day').on('click', function () {
        var today_at_midnight = new Date();
        today_at_midnight.setHours(0, 0, 0, 0);
        $.getJSON('/power/day/' + today_at_midnight.getTime()/1000, function (json) {
            createDayChart('#chart', json);
        });
    });

    $('#costs').on('click', function () {
        $.getJSON('/power/costs/' + 7 * 24 * 3600, function (json) {
            createCostChart('#chart', json);
        });
    });

    Highcharts.setOptions({
        global: {
            useUTC: false
        }
    });

    function createHistoryChart(selector, jsonData) {
        $(selector).highcharts({
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
                min: 0
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

    function createDayChart(selector, jsonData) {
        $(selector).highcharts({});
    }

    function createCostChart(selector, jsonData) {
        $(selector).highcharts({});
    }
});