$(document).ready(function () {
    Highcharts.setOptions({
        global: {
            useUTC: false
        }
    });

    chart = new Highcharts.Chart({
        chart: {
            zoomType: 'x',
            renderTo: 'chart',
            events: {
                load: function (chart) {
                    this.setTitle(null, {
                        text: 'Construit en ' + (new Date() - START) + 'ms'
                    });
                }
            },
            borderColor: '#EBBA95',
            borderWidth: 2,
            borderRadius: 10,
            ignoreHiddenSeries: false
        },
        title: {
            text: 'Consommation en Watt'
        },
        plotOptions: {
            areaspline: {
                fillColor: {
                    linearGradient: {
                        x1: 0,
                        y1: 0,
                        x2: 0,
                        y2: 1
                    }
                    ,
                    stops: [
                        [0, Highcharts.getOptions().colors[0]],
                        [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]
                    ]
                },
                marker: {
                    enabled: false
                },
                states: {
                    hover: {
                        lineWidth: 1
                    }
                }
            },
            spline: {
                marker: {
                    enabled: false
                }
            }
        },
        xAxis: {
            type: 'datetime',
            dateTimeLabelFormats: {
                hour: '%H:%M',
                day: '%H:%M',
                week: '%H:%M',
                month: '%H:%M'
            }
        },
        yAxis: [{
            title: {
                text: 'Heure Base',
                style: {
                    color: '#4572A7'
                }
            },
            labels: {
                format: '{value} W',
                style: {
                    color: '#4572A7'
                }
            },
            alternateGridColor: '#FAFAFA',
            minorGridLineWidth: 0,
            plotLines: [
                { // lignes min et max
                    value: jsonData.seuils.min,
                    color: 'green',
                    dashStyle: 'shortdash',
                    width: 2,
                    label: {
                        text: 'minimum ' + jsonData.seuils.min + 'w'
                    }
                },
                {
                    value: jsonData.seuils.max,
                    color: 'red',
                    dashStyle: 'shortdash',
                    width: 2,
                    label: {
                        text: 'maximum ' + jsonData.seuils.max + 'w'
                    }
                }
            ]
        }, {
            labels: {
                format: '{value}°C',
                style: {
                    color: '#910000'
                }
            },
            title: {
                text: 'Temperature',
                style: {
                    color: '#910000'
                }
            },
            opposite: true
        }],
        tooltip: {
            shared: true
        },
        legend: {
            layout: 'vertical',
            align: 'left',
            x: 100,
            verticalAlign: 'top',
            y: 40,
            floating: true,
            backgroundColor: '#FFFFFF'
        },
        series: [{
            name: jsonData.BASE_name,
            color: '#4572A7',
            type: 'areaspline',
            data: jsonData.BASE_data,
            tooltip: {
                valueSuffix: ' W'
            }
        }, {
            name: jsonData.Temp_name,
            data: jsonData.Temp_data,
            color: '#910000',
            yAxis: 1,
            type: 'spline',
            tooltip: {
                valueSuffix: '°C'
            }
        }, {
            name: jsonData.JPrec_name,
            data: jsonData.JPrec_data,
            color: '#89A54E',
            type: 'spline',
            width: 1,
            shape: 'squarepin',
            tooltip: {
                valueSuffix: ' W'
            }
        }]
    });
});