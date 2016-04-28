$.ajaxSetup({ cache: false });

var templateSongSmall;
var templateSongFull;

var defaultsSongSmall = {
   codec: "-",
   bitdepth: "-",
   samplerate: "-",
   bitrate: "-",
   channels: "-",
   length: "-",
   album: "-",
   artist: "-",
   title: "-",
   media: "-",
   comment: "-"
};

var defaultsSongFull = {
    album: "-",
    albumartist: "-",
    artist: "-",
    bitdepth: "-",
    bitrate: "-",
    channels: "-",
    codec: "-",
    codecprofile: "-",
    comment: "-",
    composer: "-",
    date: "-",
    genre: "-",
    length: "-",
    media: "-",
    modified: "-",
    note: "-",
    path: "-",
    performer: "-",
    samplerate: "-",
    title: "-",
    tool: "-",
    track: "-"
};

function postJSON(url, data, func, errfunc) {
   $.ajax({
      cache: false,
      type: "POST",
      url: url,
      data: JSON.stringify(data),
      success: func,
      contentType: "application/json",
      dataType: "json",
      error: errfunc
   });
}

function gotoTop() {
   $("html,body").animate({ scrollTop: 0 }, "fast");
}

function expandSong(id, el) {
   $.getJSON("/song/" + id, function(data) {
      _.defaults(data, defaultsSongFull);
      var html = $(templateSongFull(data));
      $("#" + el).replaceWith(html.hide());
      html.slideDown(250, function() {
         $('html,body').animate({scrollTop: html.offset().top},'fast');
      });
   });
}

/*
function compactSong(id, el) {
   $.getJSON("/song/" + id, function(data) {
      _.defaults(data, defaultsSongSmall);
      var html = templateSongSmall(data);
      var elem = $("#" + el);
      elem.slideUp(250, function() {
         elem.replaceWith(html);
      });
   });
}
*/

function copyValue(tag, id, el) {
   $.getJSON("/song/" + id + "/" + tag, function(data) {
       if (data[tag] !== 'undefined' && data[tag] !== "") {
          addSearchTag(tag, ":", false);
          var box = $("#searchbox");
          box.val(box.val() + data[tag]);
       }
   });

   $("#" + el).fadeOut(150).fadeIn(150);
}

function addSearchTag(tag, op, focus) {
   var box = $("#searchbox");

   if (box.val().trim() === "") {
      box.val("@" + tag + op);
   } else {
      box.val(box.val() + "\n@" + tag + op);
   }
   box.scrollTop(1000000);
   if (focus) {
      box.focus();
   }
}

$(function() {

var resultset = [];
var resultsetpos = 0;

$("#searchbox").val("");
$("#searchbox").focus();

templateSongSmall = _.template($("#template-song-small").html());
templateSongFull = _.template($("#template-song-full").html());

$.getJSON("/admin/keys", function(json) {
   json.keys.forEach(function(key) {
      var el = "<a data-searchtag='%x%' class='searchtag'>[%x%]</a> ".replace(/%x%/g, key);
      $("#command").append(el);
   });
   registerSearchtagEvents();
});

$.getJSON("/admin/info", function(json) {
    var text = "(" + json.loaded + " songs, " + Math.ceil(json.dbsize / (1024 * 1024)) + " MB)";
    $("#appinfo").text(text);

    if (json.loaded != json.found || json.warnings > 0) {
        var missing = json.found - json.loaded;
        text = "(" + missing + " songs missing, " + json.warnings + " warnings)";
        $("#appwarn").text(text);
    }
});

$("#shutdownbtn").click(function () {
    var x = confirm("SongDB will shutdown");

    if (x) {
       $.getJSON("/admin/shutdown");
    }
});

$("#clearbtn").click(function () {
    var box = $("#searchbox");
    box.val("");
    box.focus();
});

$("#searchbtn").click(function () {
    var box = $("#searchbox");
    var data = box.val();
    var json = {
       filter: data
    };

    var start = performance.now();

    postJSON("/song", json, function(response) {
        var time = ((performance.now() - start) / 1000).toFixed(2);
        $("#resultinfotext").text(response.songs.length + " result(s) in " + time + " seconds");
        var results = $("#result");
        results.empty();
        resultset = response.songs;
        resultsetpos = 0;
        appendPartialResults(results);
        $('html,body').animate({scrollTop: $("#resultinfo").offset().top});
    }, function(err) {
        var msg = $.parseJSON(err.responseText).description;
        $("#resultinfotext").text(msg);
        var results = $("#result");
        results.empty();
    });
});

$(window).scroll(function() {
   var windowEL = $(window);
   if(windowEL.scrollTop() + windowEL.height() > $(document).height() - 400) {
       appendPartialResults($("#result"));
   }
});

$("#searchbox").keyup(function (e) {
   if (e.ctrlKey && e.keyCode == 13) {
      $("#searchbtn").trigger("click");
   }
});

function appendPartialResults(container) {
   var k = Math.min(resultsetpos + 100, resultset.length);

   for(var i = resultsetpos; i < k; i++) {
      var x = resultset[i];
      _.defaults(x, defaultsSongSmall);
      container.append("<div style='will-change:transform'>" + templateSongSmall(x) + "</div>");
   }
   resultsetpos=k;
}

function registerSearchtagEvents() {
   $(".searchtag").click(function () {
      var tag = $(this).data("searchtag");
      addSearchTag(tag, "=", true);
   });
}

});


