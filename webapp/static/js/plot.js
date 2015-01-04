var populate_month_callback = function(year, month, required, paid, modified) {
    var populate_month = function(data) {
        var res = data.content,
            date = new Date(year, month, 1);
            modified = modified || data.modified;

        console.log("month " + year + " " + month);
        required.unshift({ x: date.getTime() / 1000, y: res.required });
        paid.unshift({ x: date.getTime() / 1000, y: res.paid });

    };
    return populate_month;
};

var populate_influx_callback = function(year, month, influx) {
    var populate_influx = function(data) {
        var res = data.content,
            date = new Date(year, month, 1);

        influx.unshift({ x: date.getTime() / 1000, y: res.in });
    };
    return populate_influx;
};

$(window).load(function() {
    var required = [], paid = [], influx = [];
    var today = new Date(),
        year = 1900 + today.getYear(),
        month = today.getMonth() + 1,
        urlBase = '/api/',
        modified;
    
    var requests = [];
    for(var i = 0; i < 28; ++i) {
        var url = urlBase + 'month/' + year + '/' + month + '.json';
        requests.push($.getJSON(url,
                                populate_month_callback(year, month,
                                                        required, paid,
                                                        modified)));

        url = urlBase + 'cashflow/' + year + '/' + month + '.json';
        requests.push($.getJSON(url, populate_influx_callback(year, month, influx)));

        month -= 1;
        if(month == 0) {
            month = 12;
            year -= 1;
        }
    }
    $.when.apply($, requests).then(function() {
        var lastmod = document.getElementById("lastmod");
        lastmod.innerHTML = "Last Modified " + modified;

        var palette = new Rickshaw.Color.Palette( { scheme: 'munin' } );
        var graph = new Rickshaw.Graph({
            element: document.getElementById("plot"),
            width: $("#plot").width(),
            height: $("#plot").width()*0.4,
            renderer: 'line',
            series: [
                {
                    color: palette.color(),
                    data: required,
                    name: 'Required',
                },
                {
                    color: palette.color(),
                    data: paid,
                    name: 'Paid',
                },
                {
                    color: palette.color(),
                    data: influx,
                    name: 'Cash Influx',
                },
            ]
        });
        graph.render();

        var yAxis = new Rickshaw.Graph.Axis.Y({
            graph: graph,
        });
        yAxis.render();

        var xAxis = new Rickshaw.Graph.Axis.Time({
            graph: graph,
        });
        xAxis.render();

        var legend = new Rickshaw.Graph.Legend({
            element: document.getElementById("legend"),
            graph: graph,
        });

        var hoverDetail = new Rickshaw.Graph.HoverDetail( {
            graph: graph,
            xFormatter: function(x) {
                var date = new Date(x * 1000);
               return (1900 + date.getYear()) + '/' + date.getMonth();
            }
        });
    });
});

