var CURRENT_WH = 0;

function update_power_display() {
    $("#wh").text(CURRENT_WH.toFixed(2));
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
        console.log(item);
        $("#current").text(item.temperature);
        var timestamp = moment(item.date);
        update_power_display();
        chart.series[0].addPoint([timestamp, item.temperature], true, true);
    };
    since(60 * 12);
});

function since(minutes) {
    $.getJSON('/data_since/' + minutes * 60, function (json_data) {
        var data = [];
        for (var index = 0; index < json_data.points.length; index++) {
            var point = json_data.points[index];
            data.push([new Date(point['date']).getTime(), point['watt']]);
        }
        chart.series[0].setData(data, true);
        chart.redraw();
    });
}
