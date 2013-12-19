var START = new Date();
var DAILY_CHART_BEGIN_TIMESTAMP = yesterday();

jQuery(function ($) {
    Highcharts.setOptions({
        lang: {
            months: ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'],
            weekdays: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
            decimalPoint: '.',
            thousandsSep: ',',
            rangeSelectorFrom: 'Du',
            rangeSelectorTo: 'au'
        },
        global: {
            useUTC: false
        }
    });
});

function yesterday() {
    var now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0);
}

var totalBASE = 0;
var totalHP = 0;
var totalHC = 0;
var totalprix = 0;

var chart_elec1;
var chart_elec2;

$(document).ready(function () {

    refresh_chart1(DAILY_CHART_BEGIN_TIMESTAMP);
    refresh_chart2("8jours");

    function init_chart1(data) {
        return {
            chart: {
                zoomType: 'x',
                renderTo: 'chart1',
                events: {
                    load: function (chart) {
                        this.setTitle(null, {
                            text: 'Construit en ' + (new Date() - START) + 'ms'
                        });
                        if ($('#chart1legende').length) {
                            $("#chart1legende").html(data.subtitle);
                        }
                    }
                },
                borderColor: '#EBBA95',
                borderWidth: 2,
                borderRadius: 10,
                ignoreHiddenSeries: false
            },
            title: {
                text: data.title
            },
            subtitle: {
                text: 'Construit en...'
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
            yAxis: [
                {
                    title: {
                        text: 'Heure Base'

                    },
                    labels: {
                        format: '{value} W'

                    },
                    alternateGridColor: '#FAFAFA',
                    minorGridLineWidth: 0,
                    plotLines: [
                        { // lignes min et max
                            value: data.seuils.min,
                            color: 'green',
                            dashStyle: 'shortdash',
                            width: 2,
                            label: {
                                text: 'minimum ' + data.seuils.min + 'w'
                            }
                        },
                        {
                            value: data.seuils.max,
                            color: 'red',
                            dashStyle: 'shortdash',
                            width: 2,
                            label: {
                                text: 'maximum ' + data.seuils.max + 'w'
                            }
                        }
                    ]
                },
                {
                    labels: {
                        format: '{value}°C'

                    },
                    title: {
                        text: 'Temperature',
                        style: {
                            color: '#89A54E'
                        }
                    },
                    opposite: true
                }
            ],
            tooltip: {
                shared: true
            },
            legend: {
                layout: 'vertical',
                align: 'left',
                x: 120,
                verticalAlign: 'top',
                y: 100,
                floating: true,
                backgroundColor: '#FFFFFF'
            },
            series: [
                {
                    name: data.BASE_name,
                    data: data.BASE_data,

                    id: 'BASE',
                    type: 'areaspline',
                    threshold: null,
                    tooltip: {
                        valueSuffix: ' W'
                    },
                    showInLegend: ((data.tarif_type == "HCHP") ? false : true)
                },
                {
                    name: data.Temp_name,
                    data: data.Temp_data,

                    type: 'spline',
                    yaxis: 1,
                    tooltip: {
                        valueSuffix: '°C'
                    }
                },
                {
                    name: data.JPrec_name,
                    data: data.JPrec_data,
                    type: 'spline',
                    width: 1,
                    shape: 'squarepin',
                    tooltip: {
                        valueSuffix: ' W'
                    }
                }

            ]
        }
    }

    function init_chart2(data) {
        return {
            chart: {
                renderTo: 'chart2',
                events: {
                    load: function (chart) {
                        this.setTitle(null, {
                            text: 'Construit en ' + (new Date() - START) + 'ms'
                        });
                        if ($('#chart2legende').length) {
                            $("#chart2legende").html(data.subtitle);
                        }
                    }
                },
                defaultSeriesType: 'column',
                ignoreHiddenSeries: false
            },
            credits: {
                enabled: false
            },
            title: {
                text: data.title
            },
            subtitle: {
                text: 'Construit en...'
            },
            xAxis: [
                {
                    categories: data.categories
                }
            ],
            yAxis: {
                title: {
                    text: 'kWh'
                },
                min: 0,
                minorGridLineWidth: 0,
                labels: { formatter: function () { return this.value + ' kWh' } }
            },
            tooltip: {
                formatter: function () {
                    totalBASE = data.prix.BASE * ((this.series.name == 'Heures de Base') ? this.y : this.point.stackTotal - this.y);
                    totalHP = data.prix.HP * ((this.series.name == 'Heures Pleines') ? this.y : this.point.stackTotal - this.y);
                    totalHC = data.prix.HC * ((this.series.name == 'Heures Creuses') ? this.y : this.point.stackTotal - this.y);
                    totalprix = Highcharts.numberFormat(( totalBASE + totalHP + totalHC + data.prix.abonnement ), 2);
                    tooltip = '<b> ' + this.x + ' <b><br /><b>' + this.series.name + ' ' + Highcharts.numberFormat(this.y, 2) + ' kWh<b><br />';
                    //tooltip += 'BASE : '+ Highcharts.numberFormat(totalBASE,2) + ' Euro / HP : '+ Highcharts.numberFormat(totalHP,2) + ' Euro / HC : ' + Highcharts.numberFormat(totalHC,2) + ' Euro<br />';
                    if (data.tarif_type != "HCHP") {
                        tooltip += 'BASE : ' + Highcharts.numberFormat(totalBASE, 2) + ' Euro <br />';
                    } else {
                        tooltip += 'HP : ' + Highcharts.numberFormat(totalHP, 2) + ' Euro / HC : ' + Highcharts.numberFormat(totalHC, 2) + ' Euro<br />';
                    }
                    tooltip += 'Abonnement sur la période : ' + Highcharts.numberFormat(data.prix.abonnement, 2) + ' Euro<br />';
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
                    name: data.HP_name,
                    data: data.HP_data,
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
                    showInLegend: ((data.tarif_type == "HCHP") ? true : false)
                },
                {
                    name: data.HC_name,
                    data: data.HC_data,
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
                    showInLegend: ((data.tarif_type == "HCHP") ? true : false)
                },
                {
                    name: data.BASE_name,
                    data: data.BASE_data,
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
                    showInLegend: ((data.tarif_type == "HCHP") ? false : true)
                }
            ],
            navigation: {
                menuItemStyle: {
                    fontSize: '10px'
                }
            }
        }
    }

    function refresh_chart1(date) {
        // remise à zéro du chronomètre
        START = new Date();

        $.getJSON('json.php?query=daily&date=' + parseInt(date.getTime() / 1000), function (data) {
            chart_elec1 = new Highcharts.Chart(init_chart1(data));
        });
    }

    function refresh_chart2(periode) {
        // remise à zéro du chronomètre
        START = new Date();

        $.getJSON('json.php?query=history&periode=' + periode, function (data) {
            chart_elec2 = new Highcharts.Chart(init_chart2(data));
        });
    }

    $('.button_chart1').click(function () {
        var deltaDate = parseInt(this.value);
        if (deltaDate == 0) {
            DAILY_CHART_BEGIN_TIMESTAMP = yesterday();
        }
        DAILY_CHART_BEGIN_TIMESTAMP.setDate(DAILY_CHART_BEGIN_TIMESTAMP.getDate() + deltaDate);
        refresh_chart1(DAILY_CHART_BEGIN_TIMESTAMP);
    });

    $('.button_chart2').click(function () {
        refresh_chart2(this.value);
    });

});
