$(document).ready(function () {
    moment.locale('fr');
    var CURRENT_DAY = moment().hours(0).minutes(0).seconds(0).milliseconds(0);

    Highcharts.setOptions({
        lang: {
            weekdays: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
            months: ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
        },
        global: {
            useUTC: false
        }
    });

    $('#next_day').on('click', function () {
        CURRENT_DAY.add(1, 'day');
        power.by_day(CURRENT_DAY);
    });
    $('#previous_day').on('click', function () {
        CURRENT_DAY.add(-1, 'day');
        power.by_day(CURRENT_DAY);
    });

    $('#history').on('click', function () {
        power.history();
    });

    $('#by_day').on('click', function () {
        power.by_day(CURRENT_DAY);
    });

    $('#costs').on('click', function () {
        power.costs(moment.duration(8, 'days'));
    });
    power.history();
});

var power = (function () {
     function createCostChart(selector, jsonData, config) {
        $(selector).highcharts({
                chart: {
                    defaultSeriesType: 'column',
                },
                title: {
                    text: 'Consommation électrique'
                },
                xAxis: [
                    {
                        categories: jsonData.categories
                    }
                ],
                yAxis: {
                    title: {
                        text: 'kWh'
                    },
                    min: 0,
                    minorGridLineWidth: 0,
                    labels: {formatter: function () { return this.value + ' kWh' }}
                },
                tooltip: {
                    formatter: function () {
                        var totalBASE = config.base_price * ((this.series.name == 'Heures de Base') ? this.y : this.point.stackTotal - this.y);
                        var totalHP = config.full_hours_price * ((this.series.name == 'Heures Pleines') ? this.y : this.point.stackTotal - this.y);
                        var totalHC = config.empty_hours_price * ((this.series.name == 'Heures Creuses') ? this.y : this.point.stackTotal - this.y);
                        var totalprix = Highcharts.numberFormat(( totalBASE + totalHP + totalHC + config.subscription_fee ), 2);
                        var tooltip = '<b> ' + this.x + ' <b><br /><b>' + this.series.name + ' ' + Highcharts.numberFormat(this.y, 2) + ' kWh<b><br />';
                        //tooltip += 'BASE : '+ Highcharts.numberFormat(totalBASE,2) + ' Euro / HP : '+ Highcharts.numberFormat(totalHP,2) + ' Euro / HC : ' + Highcharts.numberFormat(totalHC,2) + ' Euro<br />';
                        if (config.subscription_type === "hphc") {
                            tooltip += 'HP : ' + Highcharts.numberFormat(totalHP, 2) + ' Euro / HC : ' + Highcharts.numberFormat(totalHC, 2) + ' Euro<br />';
                        } else {
                            tooltip += 'BASE : ' + Highcharts.numberFormat(totalBASE, 2) + ' Euro <br />';
                        }
                        tooltip += 'Abonnement sur la période : ' + Highcharts.numberFormat(config.subscription_fee, 2) + ' Euro<br />';
                        tooltip += '<b> Total: ' + totalprix + ' Euro<b>';
                        return tooltip;
                    }
                },
                plotOptions: {
                    column: {
                        stacking: 'normal'
                    }
                },
                series: [
                    {
                        name: 'Heures Pleines',
                        data: jsonData.full_hours,
                        dataLabels: {
                            enabled: true,
                            color: '#FFFFFF',
                            y: 13,
                            formatter: function () {
                                return this.y;
                            },
                            style: {
                                font: 'normal 13px Verdana, sans-serif'
                            }
                        },
                        type: 'column',
                        showInLegend: true
                    },
                    {
                        name: 'Heures Creuses',
                        data: jsonData.empty_hours,
                        dataLabels: {
                            enabled: true,
                            color: '#FFFFFF',
                            y: 13,
                            formatter: function () {
                                return this.y;
                            },
                            style: {
                                font: 'normal 13px Verdana, sans-serif'
                            }
                        },
                        type: 'column',
                        showInLegend: true
                    },
                    {
                        name: 'Heures de base',
                        data: [],
                        events: {
                            click: function (e) {
                                var newdate = new Date();
                                newdate.setTime(data.debut);
                                newdate.setDate(newdate.getDate() + e.point.x);
                            }
                        },
                        dataLabels: {
                            enabled: true,
                            color: '#FFFFFF',
                            y: 13,
                            formatter: function () {
                                return this.y;
                            },
                            style: {
                                font: 'normal 13px Verdana, sans-serif'
                            }
                        },
                        type: 'column',
                        showInLegend: false
                    }
                ],
                navigation: {
                    menuItemStyle: {
                        fontSize: '10px'
                    }
                }
            }
        );
    }

    function createHistoryChart(selector, jsonData) {
        $(selector).highcharts({
            chart: {
                zoomType: 'x'
            },
            title: {
                text: 'Historique de consommation électrique par jour'
            },
            subtitle: {
                text: document.ontouchstart === undefined ?
                    'sélectionner une zone dans le graph pour zoomer' :
                    'Pinch the chart to zoom in'
            },
            navigation: {
                buttonOptions: {
                    enabled: true
                }
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
                data: jsonData,
                tooltip: {
                    valueSuffix: ' kW'
                }
            }]
        });
    }

    function createDayChart(selector, date, jsonData) {
        var max_power = Math.max(_.map(jsonData, function (date_and_power) { return date_and_power[1]; }));
        $(selector).highcharts({
            chart: {
                zoomType: 'x'
            },
            title: {
                text: 'Consommation électrique du ' + date.format('LL')
            },
            plotOptions: {
                areaspline: {
                    fillColor: {
                        linearGradient: {x1: 0, y1: 0, x2: 0, y2: 1},
                        stops: [
                            [0, Highcharts.getOptions().colors[0]],
                            [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]
                        ]
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
                    {
                        value: max_power,
                        color: 'red',
                        dashStyle: 'shortdash',
                        width: 2,
                        label: {
                            text: 'maximum ' + max_power + 'w'
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
                name: 'heures de base',
                color: '#4572A7',
                type: 'areaspline',
                data: jsonData.power,
                tooltip: {
                    valueSuffix: ' W'
                }
            }, {
                name: 'température',
                data: jsonData.temperature,
                color: '#910000',
                yAxis: 1,
                type: 'spline',
                tooltip: {
                    valueSuffix: '°C'
                }
            }, {
                name: 'période précédente',
                data: jsonData.previous,
                color: '#89A54E',
                type: 'spline',
                width: 1,
                shape: 'squarepin',
                tooltip: {
                    valueSuffix: ' W'
                }
            }],
            navigation: {
                buttonOptions: {
                    enabled: true
                }
            }
        });
    }

    return {
        history: function () {
            $(".day_navigation").hide();
            $(".cost_period").hide();
            $.getJSON('/power/history', function (json) {
                var dataWithDates = [];
                _(json.data).forEach(function (point) {
                    dataWithDates.push([Date.parse(point[0]), point[1]]);
                });
                createHistoryChart('#chart', dataWithDates);
            });
        },
        by_day: function (date) {
            $(".day_navigation").show();
            $(".cost_period").hide();
            $.getJSON('/power/day/' + date.format(), function (json) {
                var powerWithDates = [];
                var tempWithDates = [];
                _(json.day_data).forEach(function (point) {
                    var point_date = Date.parse(point[0]);
                    powerWithDates.push([point_date, point[1]]);
                    tempWithDates.push([point_date, point[2]]);
                });
                var previous_day_serie = [];
                _(json.previous_day_data).forEach(function (point) {
                    this.push([Date.parse(point[0]) + 3600 * 24 * 1000, point[1]]);
                }, previous_day_serie);
                createDayChart('#chart', date, {
                    "power": powerWithDates,
                    "temperature": tempWithDates,
                    "previous": previous_day_serie
                });
            });
        },
        costs: function (duration) {
            $(".day_navigation").hide();
            $(".cost_period").show();
            $.getJSON('/power/costs/' + moment().add(-duration).format(), function (json) {
                var categories = _(json.data).map(function(item) {return item[0]; });
                var full_hours = _(json.data).map(function(item) {return item[1][0]; });
                var empty_hours = _(json.data).map(function(item) {return item[1][1]; });
                var config = {'base_price': 0, 'full_hours_price': 0.1353, 'empty_hours_price': 0.0926, 'subscription_fee': 262.08, 'subscription_type': 'hphc'};
                createCostChart('#chart', {'categories': categories, 'full_hours': full_hours, 'empty_hours': empty_hours}, config);
            });
        }
    };
})();