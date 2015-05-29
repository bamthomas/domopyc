var CURRENT_WH = 0;
var LAST_TIMESTAMP = new Date().getTime();

function update_power_display() {
    $("#wh").text(CURRENT_WH.toFixed(2));
    $("#cost").text((CURRENT_WH * (0.0812 + 0.009 + 0.009) * 1.196 / 1000).toFixed(2));
}

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
            text: 'Consommation par jour'
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
        tooltip: {
            formatter: function () {
                return '<b>' + this.series.name + '</b><br/>' +
                    Highcharts.dateFormat('%H:%M:%S', this.x) + ': <b>' + this.y + ' w</b>';
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

    var socket = new WebSocket("ws://localhost:8080/stream");

    socket.onmessage = function (msg) {
        var item = JSON.parse(msg.data);
        $("#current").text(item.watt);
        var timestamp = new Date().getTime();
        CURRENT_WH += (timestamp - LAST_TIMESTAMP) * item.watt / (3600 * 1000);
        update_power_display();
        chart.series[0].addPoint([timestamp, item.watt], true, true);
        LAST_TIMESTAMP = timestamp;
    };
    today_chart();
});


function today_chart() {
    $.getJSON('/today', function (json_data) {
        var data = [];
        var total_minutes = 0;
        var total_watts = 0;
        for (var index = 0; index < json_data.points.length; index++) {
            var point = json_data.points[index];
            total_minutes += point['minutes'];
            total_watts += point['watt'];
            data.push([new Date(point['date']).getTime(), point['watt']]);
        }
        CURRENT_WH = (total_watts * total_minutes) / (data.length * 60);
        update_power_display();
        chart.series[0].setData(data, true);
        chart.redraw();
    });
}
function since(minutes) {
    $.getJSON('/data_since/' + minutes, function (json_data) {
        var data = [];
        for (var index = 0; index < json_data.points.length; index++) {
            var point = json_data.points[index];
            data.push([new Date(point['date']).getTime(), point['watt']]);
        }
        chart.series[0].setData(data, true);
        chart.redraw();
    });
}
