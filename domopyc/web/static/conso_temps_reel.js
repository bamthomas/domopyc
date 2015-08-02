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

    var socket = new WebSocket("wss://" + window.location.host + "/livedata/power");

    socket.onmessage = function (msg) {
        var item = JSON.parse(msg.data);
        $("#current").text(item.temperature);
        var timestamp = moment(item.date);
        var series = chart.series[0], shift = series.data.length > 170;

        console.log("item timestamp=" + timestamp + " item.temp=" + item.temperature);
        chart.series[0].addPoint([timestamp.toDate(), item.temperature], true, shift);
    };
});
