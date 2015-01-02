$(function() {
    var required = [], paid = [], influx = [];
    var today = new Date(),
        year = 1900 + today.getYear(),
        month = today.getMonth() + 1,
        urlBase = 'https://kasownik.hackerspace.pl/api/',
        modified;
    
    for(var i = 0; i < 28; ++i) {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", urlBase + 'month/'+ year + '/' + month + '.json', false);
        xhr.send();
    
        var data = JSON.parse(xhr.response),
            res = data.content,
            date = new Date(year, month, 1);
            modified = modified || data.modified;
    
        required.unshift({ x: date.getTime() / 1000, y: res.required });
        paid.unshift({ x: date.getTime() / 1000, y: res.paid });

        xhr = new XMLHttpRequest();
        xhr.open("GET", urlBase + 'cashflow/'+ year + '/' + month + '.json', false);
        xhr.send();
    
        res = JSON.parse(xhr.response).content,
        influx.unshift({ x: date.getTime() / 1000, y: res.in });
        month -= 1;
        if(month == 0) {
            month = 12;
            year -= 1;
        }
    }
    
    console.log(required, paid);
    
    var lastmod = document.getElementById("lastmod");
    lastmod.innerHTML = modified;

    var palette = new Rickshaw.Color.Palette( { scheme: 'munin' } );
    var graph = new Rickshaw.Graph({
        element: document.getElementById("plot"),
        width: 1300,
        height: 600,
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

