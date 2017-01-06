$(document).ready(function(){
    $.ajax({
        type: "GET",
        url: "http://en.wikipedia.org/w/api.php?action=parse&format=json&prop=text&section=0&page=Stack_Overflow&callback=?",
        contentType: "application/json; charset=utf-8",
        async: false,
        dataType: "json",
        success: function (data, textStatus, jqXHR) {
            var markup = data.parse.text["*"];
            var blurb = $('<div></div>').html(markup);
            // remove links as they will not work
            blurb.find('a').each(function() { $(this).replaceWith($(this).html()); });
           // remove any references
            blurb.find('sup').remove();
            // remove cite error
            blurb.find('.mw-ext-cite-error').remove();
            var blurb = $(blurb).find('p');
            var finalText = "";

            // Join together paragraphs
            for  (i = 0; i < blurb.length; i++) {
                finalText += blurb[i].innerHTML;
            }
            return finalText;
        },
        error: function (errorMessage) {
        }
    });
});