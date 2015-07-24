var INITIAL_COORDINATES = [ 54.6829976, 59.2835566 ]
var MSG_SERVER_ERROR = "Невозможно выполнить операцию: ошибка сервера"

function apiCall(uri, callback) {
    xmlhttp = new XMLHttpRequest();
    xmlhttp.open('GET', uri, true);
    xmlhttp.onreadystatechange = function() {
        if ( xmlhttp.readyState == 4 ) {
            if ( xmlhttp.status == 200 ) {
                callback(JSON.parse(xmlhttp.responseText));
            }
        }
    }
    xmlhttp.send(null);

}

function createMap(center, zoom) {
    var topo = new L.TileLayer('http://maps.marshruty.ru/ml.ashx?al=1&i=1&x={x}&y={y}&z={z}', {
        maxZoom: 15,
        minZoom: 8,
        attribution: "Генштабовские топокарты используют сервис <a href=\"http://www.marshruty.ru/Maps/Maps.aspx\">карты Маршруты.Ру</a>"
    }); 
    var osm = new L.TileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 20,
        minZoom: 8,
        attribution: "&copy; Участники <a href=\"http://www.openstreetmap.org/copyright\">OpenStreetMaps</a>"
    });
    var gs = new L.Google('SATELLITE', {
        maxZoom: 20,
        minZoom: 8
    });

    var map = L.map('map', { center: center, zoom: zoom, layers: osm  });
    var baseMaps = {
        "OpenStreetMaps": osm,
        "Топокарты": topo,
        "Google Sattelite": gs
    };
    L.control.layers(baseMaps).addTo(map);

    return map;
}

function pointPopupCode(feature) {
    name_alt = feature.properties.name_alt == "" ? "" : "<br/>(" + feature.properties.name_alt + ")";
    name = "<a href=\"/summit/" + feature.id + "\">" + feature.properties.name + "</a>";
    return name + name_alt +
        "<br/>Высота: " + feature.properties.height + 
        "<br/>Хребет:" + feature.properties.ridge;
}

function placePoints(data) {
    L.geoJson(data, {
        pointToLayer: function (feature, latlng) {
            var icon = L.MakiMarkers.icon({icon: "marker", color: "#" + feature.properties.color, size: "s"});
            return L.marker(latlng, {icon: icon}).bindPopup(pointPopupCode(feature));
        }
    }).addTo(map);
}

function fillSummitsTable(data) {
    var tb = document.getElementById("summitsTable").getElementsByTagName("tbody")[0];
    tb.innerHTML = '';
    data.features.forEach(function(f) {
        var tr = document.createElement("tr");
        var name_alt = f.properties.name_alt == "" ? "" : " (" + f.properties.name_alt + ")";
        tr.innerHTML = "<td>" + f.properties.number + "</td>" +
            "<td class=\"text-left\"><a href=\"/summit/" + f.id + "\">" + f.properties.name + name_alt + "</a></td>" +
            "<td>" + f.properties.height + "</td>" +
            "<td>" + f.properties.ridge + "</td>" 
        tb.appendChild(tr);
    });
}

function createMainMap() {
    map = createMap(INITIAL_COORDINATES, 8);
    var hash = new L.Hash(map);
    apiCall('/api/summits', placePoints);
}


function reorderSummitsTable() {
    if ( window.location.hash == '#orderByHeight' ) {
        apiCall('/api/summits?orderByHeight', fillSummitsTable);
        $('#orderSummitsByRidge').parent('li').removeClass('active');
        $('#orderSummitsByHeight').parent('li').addClass('active');
    } else {
        apiCall('/api/summits', fillSummitsTable);
        $('#orderSummitsByRidge').parent('li').addClass('active');
        $('#orderSummitsByHeight').parent('li').removeClass('active');
    }     
}

function loadSummit() {
    var sid = parseInt(window.location.href.substr(window.location.href.lastIndexOf('/') + 1));
    apiCall('/api/summits/' + sid + '?html', fillSummitPage);
}

function loadSummitEditForm() {
    var sid = document.getElementById('summit_edit_form').elements.sid.value;
    if ( parseInt(sid) > 0 ) {
        apiCall('/api/summits/' + sid, fillSummitEditForm);
    } else {
        fillSummitCreateForm();
    }
    //document.getElementById('ridge_edit_submit');
}

function fillSummitEditForm(data) {
    editedSummit = data;
    form = document.getElementById('summit_edit_form');
    form.name.value = editedSummit['properties']['name'];
    form.name_alt.value = editedSummit['properties']['name_alt'];
    form.height.value = editedSummit['properties']['height'];
    form.description.value = editedSummit['properties']['description'];
    form.coordinates.value = editedSummit['geometry']['coordinates'][1] + ', ' + editedSummit['geometry']['coordinates'][0];

    document.getElementById('map').style.height = "400px";
    map = createMap([ data.geometry.coordinates[1], data.geometry.coordinates[0] ], 12);
    document.getElementsByClassName('leaflet-container')[0].style.cursor = 'crosshair';
    marker = L.geoJson(editedSummit).addTo(map);
    map.on('click', getPointCoordinates);
    apiCall('/api/ridges', fillRidgesSelect);

}

function fillSummitCreateForm(data) {
    document.getElementById('map').style.height = "400px";
    map = createMap(INITIAL_COORDINATES, 8);
    document.getElementsByClassName('leaflet-container')[0].style.cursor = 'crosshair';
    //marker = L.geoJson(editedSummit).addTo(map);
    map.on('click', getPointCoordinates);
    apiCall('/api/ridges', fillRidgesSelect);
}

function getPointCoordinates(e) {
    document.getElementById('summit_edit_form').coordinates.value = e.latlng.lat + ', ' + e.latlng.lng;
    if (marker != null) {
        map.removeLayer(marker);
    }
    marker = L.marker(e.latlng);
    marker.addTo(map);
}

function fillRidgesSelect(data) {
    var select = document.getElementById("summit_edit_form").rid;
    data.ridges.forEach(function (r) {
        var option = document.createElement('option');
        option.value = r.id;
        option.innerHTML = r.name;
        if ( editedSummit != null && editedSummit.properties.rid == parseInt(r.id) ) {
            option.selected = true;
        }
        select.appendChild(option);
    });
}

function saveSummit(e) {
    e.preventDefault();
    if ( editedSummit == null ) {
        editedSummit = {};
        editedSummit.properties = {};
        editedSummit.geometry = {};
        editedSummit.id = 0;
    }

    // collect the form data while iterating over the inputs
    //editedRidge['properties'] = [];
    form = document.getElementById('summit_edit_form');
    editedSummit.properties.name = form.name.value;
    editedSummit.properties.name_alt = form.name_alt.value;
    editedSummit.properties.rid = parseInt(form.rid.value);
    editedSummit.properties.height = parseInt(form.height.value);
    editedSummit.properties.description = form.description.value;
    var coordinates = form.coordinates.value.split(',');
    editedSummit.geometry.coordinates = [ parseFloat(coordinates[1]), parseFloat(coordinates[0]) ];
    
    // construct an HTTP request
    var xmlhttp = new XMLHttpRequest();
    xmlhttp.open('PUT', '/api/summits/' + editedSummit.id, true);
    xmlhttp.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xmlhttp.onreadystatechange = function() {
        if ( xmlhttp.readyState == 4 ) {
            if ( xmlhttp.status == 200 ) {
                result = JSON.parse(xmlhttp.responseText);
                if (result['errors'] != null) {
                    showFormErrors(result);
                } else {
                    document.location.href = '/summits/' + result['id'];
                }
            } else {
                showFormErrors({"errors": [ MSG_SERVER_ERROR ]});
            }
        }
    }

    // send the collected data as JSON
    xmlhttp.send(JSON.stringify(editedSummit));
    return false;
}

function showFormErrors(e) {
    document.getElementById('form-errors').style.display = 'block';
    var list = document.getElementById('form-error-list');
    list.innerHTML = '';
    e.errors.forEach(function (error) {
        var listItem = document.createElement('li');
        listItem.innerHTML = error;
        list.appendChild(listItem);
    });
    window.scrollTo(0, 0);
}

function createUser(e) {
    e.preventDefault();

    var user = {};

    form = document.getElementById('register_form');
    user.name = form.name.value;
    user.email = form.email.value;
    user.pub = form.pub.checked;
    
    // construct an HTTP request
    var xmlhttp = new XMLHttpRequest();
    xmlhttp.open('POST', '/api/register', true);
    xmlhttp.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xmlhttp.onreadystatechange = function() {
        if ( xmlhttp.readyState == 4 ) {
            if ( xmlhttp.status == 204 ) {
                document.location.href = '/';
            } else if ( xmlhttp.status == 200 ) {
                result = JSON.parse(xmlhttp.responseText);
                showFormErrors(result);
            } else {
                showFormErrors({"errors": [ MSG_SERVER_ERROR ]});
            }
        }
    }
    xmlhttp.send(JSON.stringify(user));
}

function submitForm(e) {
  e.preventDefault();

  var form = e.target;
  var params = /*[].filter.call(form.elements, function(el) {
        console.log(el);
        //Allow only elements that don't have the 'checked' property
        //Or those who have it, and it's checked for them.
        return typeof(el.checked) === 'undefined' || el.checked;
        //Practically, filter out checkboxes/radios which aren't checekd.
    })*/
    [].filter.call(form.elements, function(el) { return !!el.name; }) //Nameless elements die.
    .filter(function(el) { return ! el.disabled; }) //Disabled elements die.
    .map(function(el) {
        //Map each field into a name=value string, make sure to properly escape!
        return encodeURIComponent(el.name) + '=' + encodeURIComponent(el.value);
    }).join('&'); //Then join all the strings by &
  xmlhttp.open(form.method, form.action, true);
  xmlhttp.setRequestHeader('Content-Type', 'application/x-form-urlencoded');

  xmlhttp.onload = formSubmitted;

  xmlhttp.send(params);
}

function formSubmitted(e) {
  console.log(e);
}

function addClimb(e) {
    e.preventDefault();

    var climb = {};

    form = document.getElementById('climb_form');
    climb.summit = parseInt(form.sid.value);
    climb.ts = form.ts.value;
    climb.comment = form.comment.value;
    
    console.log(climb);
}
