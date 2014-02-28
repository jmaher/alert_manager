/* -*- Mode: JS; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set sw=2 ts=2 et tw=80 : */

"use strict";

var alertID = '';

var AddCommentUI = {

  numSendingComments: 0,
  numSendingCommentChangedCallback: function empty() {},

  init: function AddCommentUI_init(submitURL) {
    var self = this;
    $("a.addNote").live("click", function addNoteLinkClick() {
      self.openCommentBox(-1, "");
      return false;
    });
    $("#logNoteEmail").bind("change", function logNoteEmailChange() {
      self._setEmail(this.value);
    });
    $("#logNoteEmail").val(self._getEmail());
    $("#addNotePopup").get(0).afterCloseCallback = function resetAfterClosed() {
    };

    $("#addNoteForm").bind("submit", function addNoteFormSubmit() {
      self.submit();
      $("#addNotePopup").hide();
      return false;
    });

    $("#logNoteText").bind("keyup", function logNoteTextKeypress(e) {
      // Control+Enter submits the form
      if (e.which == 13 && (e.ctrlKey || e.metaKey)) {
        $("#addNoteForm").submit();
        return false;
      }
    });

    // Defeat the keep-text-on-reload feature, because it results in
    // comments containing changesets that are no longer selected.
    $("#logNoteText").val('');
  },

  submit: function AddCommentUI_submit() {
    var self = this;
    var email = $("#logNoteEmail").val();
    var status = $("#logNoteStatus").val();
    var bug = $("#logNoteBug").val();
    var comment = $("#logNoteText").val();
    self._postOneTBPLNote(alertID, email, comment, status, bug);
  },

  openCommentBox: function AddCommentUI_openCommentBox(id, body) {
    $(".lnBody").html("<pre>" + body + "</pre>");
    $("#addNotePopup").show();
    alertID = id;
    var focusTextfield = ($("#logNoteEmail").val() ? $("#logNoteText") : $("#logNoteEmail")).get(0);
    focusTextfield.focus();
    focusTextfield.select();
  },

  _getEmail: function AddCommentUI__getEmail() {
    return this.email || "";
  },

  _setEmail: function AddCommentUI__setEmail(email) {
    this.email = email;
  },

  _popupIsOpen: function AddCommentUI__popupIsOpen() {
    return $("#addNotePopup").is(":visible");
  },

  _postOneTBPLNote: function AddCommentUI__postOneTBPLNote(alertID, email, comment, status, bugid) {
    $.ajax({
      url: "http://localhost:8157/data/submit",
      type: "POST",
      data: {
        id: alertID,
        email: email,
        comment: comment,
        status: status,
        bug: bugid,
      }
    });
  },
};

var AddDuplicateUI = {
  init: function addDuplicateUI_init(submitURL) {
    var self = this;
    $("#addDuplicateForm").bind("submit", function addDuplicateFormSubmit() {
      self.submit();
      $("#addDuplicatePopup").hide();
      return false;
    });
    $("#logDuplicateText").val('');
  },

  submit: function addDuplicateUI_submit() {
    var self = this;
    var duprev = $("#logDuplicateText").val();
    self._postDuplicate(alertID, duprev);
    return false;
  },

  openDuplicateBox: function addDuplicateUI_openDuplicateBox(id, duplicate) {
    $("#addDuplicatePopup").show();
    alertID = id;
    
    var focusTextfield = $("#logDuplicateText");
    focusTextfield.val(duplicate);
    focusTextfield.focus();
    focusTextfield.select();
  },

  _postDuplicate: function addDuplicateUI__postDuplicate(alertID, duprev) {
    $.ajax({
      url: "http://localhost:8157/data/submitduplicate",
      type: "POST",
      data: {
        id: alertID,
        duplicate: duprev,
        status: 'Duplicate',
      }
    });
  },
};

var AddBugUI = {
  init: function addBugUI_init(submitURL) {
    var self = this;
    $("#addBugForm").bind("submit", function addBugFormSubmit() {
      self.submit();
      $("#addBugPopup").hide();
      return false;
    });
    $("#logBugText").val('');
  },

  submit: function addBugUI_submit() {
    var self = this;
    var bugID = $("#logBugText").val();
    var status = $("#logBugStatusText").val();
    self._postBug(alertID, bugID, status);
    return false;
  },

  openBugBox: function addBugUI_openBugBox(id, bug, status) {
    $("#addBugPopup").show();
    alertID = id;

    if (status == "NEW") {
        status = "Investigating";
    }
    $("#logBugStatusText").val(status);
    
    var focusTextfield = $("#logBugText");
    focusTextfield.val(bug);
    focusTextfield.focus();
    focusTextfield.select();
  },

  _postBug: function addBugUI__postBug(alertID, bugID, status) {
    $.ajax({
      url: "http://localhost:8157/data/submitbug",
      type: "POST",
      data: {
        id: alertID,
        bug: bugID,
        status: status,
      }
    });
  },
};
