var root_url = window.location.protocol + '//' + window.location.host;

function loadSelectors() {
    $.getJSON(root_url + "/getvalues", function (data) {

        function compare(a, b) {
            a = a.toString().toLowerCase();
            b = b.toString().toLowerCase();
            if (a < b)
                return -1;
            if (a > b)
                return 1;
            return 0;
        }

        var tests = data['test'].sort(compare);
        var revs = data['rev'];
        var platforms = data['platform'].sort(compare);
        if (parseInt(results['showAll']) == 1) {
            document.getElementById("checkbox").checked = true;
        }

        for (var i in tests) {
            var newoption = document.createElement("option");
            newoption.id = "test";
            var value = tests[i][0];
            $("#test").append("<option value=\"" + value + "\">" + value + "</option>");
        }

        for (i in revs) {
            var newoption = document.createElement("option");
            newoption.id = "rev";
            var value = revs[i][0];
            $("#rev").append("<option value=\"" + value + "\">" + value + "</option>");
        }

        for (i in platforms) {
            var newoption = document.createElement("option");
            newoption.id = "platform";
            var value = platforms[i][0];
            $("#platform").append("<option value=\"" + value + "\">" + value + "</option>");
        }

        try {
            document.getElementById("rev").value = results['rev'];
            document.getElementById("test").selectedIndex = results['testIndex'];
            document.getElementById("platform").selectedIndex = results['platIndex'];
        } catch (e) {
            throw e;
        }

    });

    $('#button').click(function () {
        var rev = $('#rev').val();
        var test = $('#test').val();
        var platform = $('#platform').val();
        var showall = 0;
        var testIndex = $("select[id='test'] option:selected").index();
        var platIndex = $("select[id='platform'] option:selected").index();
        if ($('#checkbox').is(":checked")) {
            console.log("checked");
            showall = 1;
        }
        document.cookie = "platform = " + platform;
        document.cookie = "test = " + test;

        var href = "alerts.html";
        var flag = '?';
        if (rev && rev != '') {
            href += flag + "rev=" + rev;
            flag = '&';
        }
        if (showall && showall != '') {
            href += flag + "showAll=" + showall;
            flag = '&';
        }
        if (testIndex && testIndex != '') {
            href += flag + "testIndex=" + testIndex;
            flag = '&';
        }
        if (platIndex && platIndex != '') {
            href += flag + "platIndex=" + platIndex;
            flag = '&';
        }
        location.href = href;

    });
}


function hideMerged(originalkeyrev, showall) {
    var req = new XMLHttpRequest();
    req.onload = function (e) {
        var raw_data = JSON.parse(req.response);

        var fields = ["date", "branch", "test", "platform", "percent", "graphurl", "changeset", "tbplurl", "comment", "bug", "status"]
        var alerts = raw_data.alerts;

        var keyrev = "";
        var tbl = "";
        // insert revisions into lower table
        for (var alert in alerts) {
            if (alerts[alert]["mergedfrom"] == originalkeyrev) {
                tbl = document.getElementById(originalkeyrev + "-tbl");
            } else {
                continue;
            }
            var row = $(document.getElementById(alerts[alert]["id"] + "-" + originalkeyrev));
            if (row) {
                row.remove();
            }
        }
        var mergedfromhtml = "<span id=\"mergedfrom-" + originalkeyrev + "\" onclick=\"showMerged('" + originalkeyrev + "', " + showall + ");\">view merged alerts</span>";

        $(document.getElementById(originalkeyrev + "-hdr")).html("<a href=?rev=" + originalkeyrev + "&showall=1&testIndex=0&platIndex=0><h3>" + originalkeyrev + "</h3></a>" + mergedfromhtml);
    }
    req.open('get', root_url + '/mergedalerts?keyrev=' + originalkeyrev, true);
    req.send();
}

function showMerged(originalkeyrev, showall) {
    var req = new XMLHttpRequest();
    req.onload = function (e) {
        var raw_data = JSON.parse(req.response);
        var alerts = raw_data.alerts;

        var tbl = "";
        // insert revisions into lower table
        for (var alert in alerts) {
            if (alerts[alert]["mergedfrom"] != originalkeyrev) {
                continue;
            }
            tbl = document.getElementById(originalkeyrev + "-tbl");
            addAlertToUI(tbl, alerts[alert], showall, originalkeyrev);
        }
        var mergedfromhtml = "<span id=\"mergedfrom-" + originalkeyrev + "\" onclick=\"hideMerged('" + originalkeyrev + "', " + showall + ");\">hide merged alerts</span>";
        $(document.getElementById(originalkeyrev + "-hdr")).html("<h3><a href=?rev=" + originalkeyrev + "&showall=1&testIndex=0&platIndex=0>" + originalkeyrev + "</a></h3>" + mergedfromhtml);
    }
    req.open('get', root_url + '/mergedalerts?keyrev=' + originalkeyrev, true);
    req.send();
}

function addMergedLinks(showall) {
    var req = new XMLHttpRequest();
    req.onload = function (e) {
        var raw_data = JSON.parse(req.response);

        var fields = ["id", "date", "bug", "status", "keyrevision", "bugcount", "mergedfrom"]
        var alerts = raw_data.alerts;

        var count = 0;
        for (var alert in alerts) {
            if (alerts[alert]['mergedfrom'] != '') {
                var mf = alerts[alert]['mergedfrom'];
                if ($(document.getElementById(mf + "-hdr")).html() == "") {
                    continue;
                }

                var mergedfromhtml = "<span id=\"mergedfrom-" + mf + "\" onclick=\"showMerged('" + mf + "', " + showall + ");\">view merged alerts</span>";
                $(document.getElementById(mf + "-hdr")).html("<a href=?rev=" + mf + "&showAll=1&testIndex=0&platIndex=0><h3>" + mf + "</a></h3>" + mergedfromhtml);
            }
        }
    }
    req.open('get', root_url + '/mergedids', true);
    req.send();
}

function updateStatus(alertid, duplicate, bugid, mergedfrom) {
    var status = $(document.getElementById(alertid + "-status")).val();
    if (status == 'Duplicate') {
        // popup window with field for duplicate, seeded with alert['duplicate']
        // consider merged rev if needed
        suggestedDuplicate = duplicate;
        if (suggestedDuplicate == 'null' || suggestedDuplicate == '') {
            suggestedDuplicate = mergedfrom;
        }

        AddDuplicateUI.openDuplicateBox(alertid, suggestedDuplicate);
    } else if (status == 'Backout') {
        var bug = bugid;
        if (bug == '') {
            bug = $(document.getElementById(alertid + "-bug")).val();
        }
        AddBugUI.openBugBox(alertid, bug, 'Backout');
    } else {
        $.ajax({
            url: "updatestatus",
            type: "POST",
            data: {
                id: alertid,
                status: status,
            }
        });
    }
}

function updateBug(alertid, bugid, status) {
    var bug = bugid;
    if (bug == '') {
        bug = $(document.getElementById(alertid + "-bug")).val();
    }
    if (status == '') {
        status = 'NEW';
    }

    AddBugUI.openBugBox(alertid, bug, status);
}

function updateTbplURL(alertid, tbplurl) {
    AddTbplUI.openTbplBox(alertid, tbplurl);
}

function addAlertToUI(tbl, alert, showall) {
    addMergedAlertToUI(tbl, alert, showall, "");
}


// Function idDescending sorts the objects in the descending order of their id. This way, we can view the most recent alerts at the top.
// The objects have been sorted based on their id and not on their date as sorting by the date field was not working.
function idDescending(a, b) {
    if (a["id"] < b["id"]) {
        return 1;
    }
    else {
        return -1;
    }
}

function loadAllAlerts(showall, rev, test, platform, current) {
    var req = new XMLHttpRequest();
    req.onload = function (e) {
        var raw_data = JSON.parse(req.response);
        var alerts = raw_data.alerts;
        alerts.sort(idDescending);

        var keyrev = "";
        var tbl = "";
        // insert revisions into lower table
        for (var alert = 0; alert < alerts.length; alert++) {
            if (alerts[alert]["keyrevision"] != keyrev) {
                keyrev = alerts[alert]["keyrevision"];
                if ($(document.getElementById(keyrev + "-hdr")).html() == null) {
                    var newdiv = document.createElement("div");
                    newdiv.id = keyrev;
                    $("#revisions").append(newdiv);

                    $(document.getElementById(keyrev)).append("<span id=\"" + keyrev + "-hdr\"><a href=?rev=" + keyrev + "&showall=1&testIndex=0&platIndex=0><h3>" + keyrev + "</h3></a></span>");

                }
                if ($(document.getElementById(keyrev + "-tbl")).html() == null) {
                    var kdiv = document.getElementById(keyrev);
                    var newtbl = document.createElement("table");
                    newtbl.id = keyrev + '-tbl';
                    $(document.getElementById(keyrev)).append(newtbl);
                }

                $(document.getElementById(keyrev + "-hdr")).html("<a href=?rev=" + keyrev + "&showall=1&testIndex=0&platIndex=0><h3>" + keyrev + "</h3></a>");
                tbl = document.getElementById(keyrev + "-tbl");
            }
            var r = addAlertToUI(tbl, alerts[alert], showall);
            if ($(document.getElementById(keyrev + '-tbl')).find('tr').size() == 0) {
                $(document.getElementById(keyrev + "-hdr")).html("");
            }
        }
        addMergedLinks(showall);
        AddCommentUI.init();
        AddDuplicateUI.init();
        AddBugUI.init();
        AddTbplUI.init();
    }
    if (current == "true") {
        url = "/alertsbyrev";
    } else {
        url = "/alertsbyexpiredrev";
    }
    flag = '?';
    if (rev && rev != '') {
        url += flag + "rev=" + rev;
    }
    if (test && test != '') {
        url += flag + "test=" + test;
    }
    if (platform && platform != '') {
        url += flag + "platform=" + platform;
    }
    req.open('get', (root_url + url), true);
    req.send();
}

function editAlert(id, body) {
    return function () {
        AddCommentUI.openCommentBox(id, body);
    }
}

function hideDiv(name) {
    document.getElementById(name).style.display = "none";
}

function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for (var i = 0; i < ca.length; i++) {
        var c = ca[i].trim();
        if (c.indexOf(name) == 0) return c.substring(name.length, c.length);
    }
    return "";
}

function getJsonFromUrl() {
    var query = location.search.substr(1);
    var data = query.split("&");
    var result = {};
    for (var i = 0; i < data.length; i++) {
        var item = data[i].split("=");
        if (item[0].trim().length > 0) result[item[0]] = item[1];
    }
    return result;
}


//RETURN FIRST NOT NULL, AND DEFINED VALUE
function nvl() {
    var args = arguments.length == 1 ? arguments[0] : arguments;
    var a;
    for (var i = 0; i < args.length; i++) {
        a = args[i];
        if (a !== undefined && a != null) return a;
    }//for
    return null;
}//method

coalesce = nvl;
