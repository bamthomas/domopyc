var START = new Date();
var DAILY_CHART_BEGIN_TIMESTAMP = yesterday();

function yesterday() {
    var now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0);
}

var totalBASE = 0;
var totalHP = 0;
var totalHC = 0;
var totalprix = 0;

var chart_elec2;

$(document).ready(function () {
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

    refresh_chart1(DAILY_CHART_BEGIN_TIMESTAMP);
    refresh_chart2("8jours");

    function init_chart2(data) {
        return     }

    function refresh_chart1(date) {
        // remise à zéro du chronomètre
        START = new Date();

        $.getJSON('json.php?query=daily&date=' + parseInt(date.getTime() / 1000), function (jsonData) {
            $('#chart1').highcharts();
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
