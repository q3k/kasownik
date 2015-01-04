var urlBase = '/api/';
var months_back = 28;

var populate_month_callback = function(i, d, url, year, month, required, paid) {
    var populate_month = function(data) {
        var res = data.content,
            date = new Date(year, month, 1);

        console.log("month " + year + " " + month);
        required.unshift({ x: date.getTime() / 1000, y: res.required });
        paid.unshift({ x: date.getTime() / 1000, y: res.paid });
        i = i - 1;
        var width = 100 - (i * (100.0 / months_back));
        $("#loadprogress .progress-bar").attr("style", "width: " + width + "%");
        if (i == 0)
        {
            d.resolve(data.modified);
        }
        else
        {
            month -= 1;
            if(month == 0) {
                month = 12;
                year -= 1;
            }
            url = urlBase + 'month/' + year + '/' + month + '.json';
            $.getJSON(url, populate_month_callback(i, d, url,
                                                   year, month,
                                                   required, paid));
        }
    };
    return populate_month;
};

var populate_influx_callback = function(i, d, url, year, month, influx) {
    var populate_influx = function(data) {
        var res = data.content,
            date = new Date(year, month, 1);

        influx.unshift({ x: date.getTime() / 1000, y: res.in });
        i = i - 1;
        if (i == 0)
        {
            d.resolve();
        }
        else
        {
            month -= 1;
            if(month == 0) {
                month = 12;
                year -= 1;
            }
            url = urlBase + 'cashflow/' + year + '/' + month + '.json';
            $.getJSON(url, populate_influx_callback(i, d, url,
                                                   year, month,
                                                   influx));
        }
    };
    return populate_influx;
};

$(window).load(function() {
    var required = [], paid = [], influx = [];
    var today = new Date(),
        year = 1900 + today.getYear(),
        month = today.getMonth() + 1;
    
    var d1 = $.Deferred();
    var url1 = urlBase + 'month/' + year + '/' + month + '.json';
    $.getJSON(url1, populate_month_callback(months_back, d1, url1,
                                            year, month,
                                            required, paid));
    var d2 = $.Deferred();
    var url2 = urlBase + 'cashflow/' + year + '/' + month + '.json';
    $.getJSON(url2, populate_influx_callback(months_back, d2, url2,
                                             year, month, influx));
    $.when(d1, d2).then(function(modified) {
        $("#lastmod").text("Last modified: " + modified);
        $("#loadprogress").hide();
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

