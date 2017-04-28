$(document).ready(function () {
    moment.locale('fr');

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

    power.day();
});

var power = (function () {
    var CURRENT_DAY = moment().hours(0).minutes(0).seconds(0).milliseconds(0);
    var socket = null;


    function createCostChart(selector, jsonData, config) {
        $(selector).highcharts({
                chart: {
                    defaultSeriesType: 'column'
                },
                title: {
                    text: 'Consommation électrique'
                },
                xAxis: {
                    categories: jsonData.categories
                },
                yAxis: {
                    title: {
                        text: 'kWh'
                    },
                    min: 0,
                    minorGridLineWidth: 0,
                    labels: {formatter: function () { return this.value + ' kWh' }},

                },
                tooltip: {
                    formatter: function () {
                        var totalBASE = config.base_price * ((this.series.name == 'Heures de Base') ? this.y : this.point.stackTotal - this.y);
                        var totalHP = config.full_hours_price * ((this.series.name == 'Heures Pleines') ? this.y : this.point.stackTotal - this.y);
                        var totalHC = config.empty_hours_price * ((this.series.name == 'Heures Creuses') ? this.y : this.point.stackTotal - this.y);
                        var totalprix = Highcharts.numberFormat(( totalBASE + totalHP + totalHC), 2);
                        var tooltip = '<b> ' + this.x + ' <b><br /><b>' + this.series.name + ' ' + Highcharts.numberFormat(this.y, 2) + ' kWh<b><br />';
                        if (config.subscription_type === "hphc") {
                            tooltip += 'HP : ' + Highcharts.numberFormat(totalHP, 2) + ' € / HC : ' + Highcharts.numberFormat(totalHC, 2) + ' €<br />';
                        } else {
                            tooltip += 'BASE : ' + Highcharts.numberFormat(totalBASE, 2) + ' € <br />';
                        }
                        tooltip += '<b> Total: ' + totalprix + ' €<b>';
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
                            format: '{y:,.0f}'
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
                            format: '{y:,.0f}'
                        },
                        type: 'column',
                        showInLegend: true
                    },
                    {
                        name: 'Heures de base',
                        data: [],
                        dataLabels: {
                            enabled: true,
                            color: '#FFFFFF',
                            format: '{y:,.0f}'
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
                    text: 'énergie (kWh)'
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
                },
                series: {
                    cursor: 'pointer',
                    point: {
                        events: {
                            click: function () {
                                CURRENT_DAY = moment(this.x);
                                power.by_day(CURRENT_DAY);
                            }
                        }
                    }
                }
            },
            series: [{
                type: 'area',
                name: 'Consommation',
                data: jsonData,
                tooltip: {
                    valueSuffix: ' kWh'
                }
            }]
        });
    }

    function createDayChart(selector, date, jsonData) {
        var highcharts_settings = {
            chart: {
                zoomType: 'x'
            },
            title: {
                text: 'Consommation électrique du ' + date.format('LL')
            },
            plotOptions: {
                areaspline: {
                    fillColor: {
                        linearGradient: {
                            x1: 0,
                            y1: 0,
                            x2: 0,
                            y2: 1
                        },
                        stops: [
                            [0, Highcharts.getOptions().colors[0]],
                            [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]
                        ]
                    }
                }
            },
            xAxis: {
                type: 'datetime'
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
                minorGridLineWidth: 0
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
        };
        $(selector).highcharts(highcharts_settings);
    }

    function get_time_format(moment_duration) {
        // iso than current_cost_mysql.get_sql_period_function()
        if (moment_duration >= moment.duration(11, 'weeks')) {
            return 'MMM';
        }
        if (moment_duration >= moment.duration(15, 'days')) {
            return 'W';
        }
        else return 'L';
    }

    function datify(date_data_serie, data_index) {
        return _.map(date_data_serie, function (date_data) {
            return [Date.parse(date_data[0]), date_data[data_index]];
        });
    }

    return {
        next_day: function () {
            CURRENT_DAY.add(1, 'day');
            this.by_day(CURRENT_DAY);
        },
        previous_day: function () {
            CURRENT_DAY.add(-1, 'day');
            this.by_day(CURRENT_DAY);
        },
        history: function () {
            $(".day_navigation").hide();
            $(".cost_period").hide();
            $.getJSON('/power/history', function (json) {
                createHistoryChart('#chart', datify(json.data, 1));
            });
        },
        day: function () {
            this.by_day(CURRENT_DAY);
        },
        by_day: function (date) {
            $(".day_navigation").show();
            $(".cost_period").hide();
            $.getJSON('/power/day/' + date.format('YYYY-MM-DDTHH:mm:ss'), function (json) {
                var previous_day_serie = _.map(json.previous_day_data, function (point) {
                    return [Date.parse(point[0]) + 3600 * 24 * 1000, point[1]];
                });
                createDayChart('#chart', date, {
                    "power": datify(json.day_data, 1),
                    "temperature": datify(json.day_data, 2),
                    "previous": previous_day_serie
                });
            });
        },
        costs: function (duration) {
            $(".day_navigation").hide();
            $(".cost_period").show();
            $.getJSON('/power/costs/' + moment().add(-duration).format('YYYY-MM-DDTHH:mm:ss'), function (json) {
                var categories = _(json.data).map(function (item) {return moment(item[0]).format(get_time_format(duration)); });
                var full_hours = _(json.data).map(function (item) {return item[1][0]; });
                var empty_hours = _(json.data).map(function (item) {return item[1][1]; });
                createCostChart('#chart', {
                    'categories': categories,
                    'full_hours': full_hours,
                    'empty_hours': empty_hours
                }, CONFIGURATION);
            });
        },
        close_socket: function() {
            if (socket != null) {
                socket.close();
                socket = null;
            }
        },
        real_time: function () {
            $(".cost_period").hide();
            socket = new WebSocket("wss://" + window.location.host + "/livedata/power");
            var chart = new Highcharts.Chart({
                chart: {
                    renderTo: 'chart',
                    type: 'areaspline',
                    marginRight: 10
                },
                title: {
                    text: 'Consommation en temps réel'
                },
                xAxis: {
                    type: 'datetime',
                    tickPixelInterval: 150
                },
                yAxis: {
                    title: {
                        text: 'Watt'
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
                        name: 'Consommation courante',
                        data: []
                    }
                ]
            });

            socket.onmessage = function (msg) {
                var item = JSON.parse(msg.data);
                var timestamp = moment(item.date);
                var series = chart.series[0], shift = series.data.length > 170;

                console.log("item timestamp=" + timestamp + " item.watt=" + item.watt);
                chart.series[0].addPoint([timestamp.toDate().getTime(), item.watt], true, shift);
            };

        }
    };
})();