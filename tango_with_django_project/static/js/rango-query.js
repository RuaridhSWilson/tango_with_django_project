/*
$(document).ready(function() {
    alert("Hello, world!");
});*/

$(document).ready(function () {

    $("#about-btn").click(function () {
        alert("You clicked the button using JQuery!");
        $(this).removeClass("btn-primary").addClass("btn-success");

        msgStr = $("#msg").html();
        msgStr = msgStr + " ooo, fancy!";
        $("#msg").html(msgStr);
    });

    $("p").hover(
        function () {
            $(this).css("color", "red");
        },
        function () {
            $(this).css("color", "black");
        }
    );
});
