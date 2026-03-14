/**
 * CDJ-100X Mixxx Controller Script
 *
 * Based on XDJ100SX.js — adapted for the CDJ-100X rework project.
 * Handles: jog wheel, pitch fader (14-bit), cue, search, hot cues,
 * loop rolls, beat jumps, key shift, and library browsing.
 */

var CDJ100X = {};
CDJ100X.currentMode = 0;
CDJ100X.lastJogMoveTime = 0;

// --- Init / Shutdown ---

CDJ100X.init = function () {
    // Set default filter mode (Mode 0 = Hot Cue A,B,C)
    engine.setValue("[Channel2]", "filterLowKill", 1);
    engine.setValue("[Channel2]", "filterMidKill", 0);
    engine.setValue("[Channel2]", "filterHighKill", 0);
    engine.setValue("[Channel3]", "filterLowKill", 0);
    engine.setValue("[Channel3]", "filterMidKill", 0);
    engine.setValue("[Channel3]", "filterHighKill", 0);
};

CDJ100X.shutdown = function () {
    // Turn off all LEDs
    var ledNotes = [0x41, 0x3D, 0x40, 0x3E, 0x3F];
    for (var i = 0; i < ledNotes.length; i++) {
        midi.sendShortMsg(0x80, ledNotes[i], 0x00);
    }
};

// --- Jog Wheel ---

CDJ100X.JogWheelEnabled = false;

CDJ100X.nudgeWheelTurn = function (channel, control, value, status, group) {
    CDJ100X.lastJogMoveTime = Date.now();
    var newValue = value - 64;
    var deckNumber = script.deckFromGroup(group);

    if (engine.isScratching(deckNumber)) {
        engine.scratchTick(deckNumber, newValue);
        CDJ100X.JogWheelEnabled = false;
    } else {
        engine.setValue(group, "jog", newValue);
        CDJ100X.JogWheelEnabled = true;
    }
};

// --- Search Buttons ---

CDJ100X.searchButton = function (channel, control, value, status, group) {
    var NOTE_SEARCH_FORWARD = 0x43;
    var NOTE_SEARCH_BACKWARD = 0x42;
    var isJogActive = (Date.now() - CDJ100X.lastJogMoveTime < 100);

    if (isJogActive) {
        if (control === NOTE_SEARCH_FORWARD) {
            if (value === 127) {
                script.triggerControl(group, "rateSearch_up", 1);
            }
            if (value === 0) {
                script.triggerControl(group, "rateSearch_set_zero", 1);
            }
        } else if (control === NOTE_SEARCH_BACKWARD) {
            if (value === 127) {
                script.triggerControl(group, "rateSearch_down", 1);
            }
            if (value === 0) {
                script.triggerControl(group, "rateSearch_set_zero", 1);
            }
        }
    } else {
        if (control === NOTE_SEARCH_FORWARD) {
            if (value === 127) {
                script.triggerControl(group, "rateSearch_up_small", 1);
            }
            if (value === 0) {
                script.triggerControl(group, "rateSearch_set_zero", 1);
            }
        } else if (control === NOTE_SEARCH_BACKWARD) {
            if (value === 127) {
                script.triggerControl(group, "rateSearch_down_small", 1);
            }
            if (value === 0) {
                script.triggerControl(group, "rateSearch_set_zero", 1);
            }
        }
    }
};

// --- Pitch Ranges ---

CDJ100X.rateRanges = [0.08, 0.10, 0.16, 0.24, 0.50];
CDJ100X.currentRange = 0;

// --- Beat Jump Ranges ---

CDJ100X.BeatJumpRanges = [4, 8, 16, 32, 64, 128];
CDJ100X.currentBeatJumpRange = 3;

// --- Shift ---

CDJ100X.shiftPressed = false;

CDJ100X.shift = function (channel, control, value, status, group) {
    if (value === 127) {
        CDJ100X.shiftPressed = true;
    } else {
        CDJ100X.shiftPressed = false;
    }
};

// --- Master Tempo & Tempo Range ---

CDJ100X.key = function (channel, control, value, status, group) {
    if (CDJ100X.shiftPressed) {
        if (value) {
            CDJ100X.currentRange++;
            if (CDJ100X.currentRange >= CDJ100X.rateRanges.length) {
                CDJ100X.currentRange = 0;
            }
            engine.setValue(group, "rateRange", CDJ100X.rateRanges[CDJ100X.currentRange]);
        }
    } else {
        script.toggleControl(group, "keylock", 100);
    }
};

// --- Button Mode ---

CDJ100X.buttonMode = function (channel, control, value, status, group) {
    if (value > 0) {
        CDJ100X.currentMode = (CDJ100X.currentMode + 1) % 6;

        // Reset all mode indicators
        engine.setValue("[Channel2]", "filterLowKill", 0);
        engine.setValue("[Channel2]", "filterMidKill", 0);
        engine.setValue("[Channel2]", "filterHighKill", 0);
        engine.setValue("[Channel3]", "filterLowKill", 0);
        engine.setValue("[Channel3]", "filterMidKill", 0);
        engine.setValue("[Channel3]", "filterHighKill", 0);

        // Set current mode indicator
        if (CDJ100X.currentMode === 0) {
            engine.setValue("[Channel2]", "filterLowKill", 1);
        } else if (CDJ100X.currentMode === 1) {
            engine.setValue("[Channel2]", "filterMidKill", 1);
        } else if (CDJ100X.currentMode === 2) {
            engine.setValue("[Channel2]", "filterHighKill", 1);
        } else if (CDJ100X.currentMode === 3) {
            engine.setValue("[Channel3]", "filterLowKill", 1);
        } else if (CDJ100X.currentMode === 4) {
            engine.setValue("[Channel3]", "filterMidKill", 1);
        } else {
            engine.setValue("[Channel3]", "filterHighKill", 1);
        }
    }
};

// --- Multi-function Buttons (Jet, Zip, Wah) ---
//
// Mode 0: Hot Cue A, B, C
// Mode 1: Hot Cue D, E, F
// Mode 2: Hot Cue G, H
// Mode 3: Loop Roll 1/8, 1/4, 1/2
// Mode 4: Beat Jump Back, Forward, Change Size
// Mode 5: Key Shift -, +, Reset

CDJ100X.button = function (buttonNumber) {
    return function (channel, control, value, status, group) {
        if (value === 127) {
            // Hot Cue A, B, C
            if (CDJ100X.currentMode === 0) {
                if (CDJ100X.shiftPressed) {
                    engine.setValue(group, "hotcue_" + buttonNumber + "_clear", 1);
                } else {
                    engine.setValue(group, "hotcue_" + buttonNumber + "_activate", 1);
                }
            }
            // Hot Cue D, E, F
            if (CDJ100X.currentMode === 1) {
                var mode = buttonNumber + 3;
                if (CDJ100X.shiftPressed) {
                    engine.setValue(group, "hotcue_" + mode + "_clear", 1);
                } else {
                    engine.setValue(group, "hotcue_" + mode + "_activate", 1);
                }
            }
            // Hot Cue G, H
            if (CDJ100X.currentMode === 2) {
                var mode = buttonNumber + 6;
                if (CDJ100X.shiftPressed) {
                    engine.setValue(group, "hotcue_" + mode + "_clear", 1);
                } else {
                    engine.setValue(group, "hotcue_" + mode + "_activate", 1);
                }
            }
            // Loop Roll
            if (CDJ100X.currentMode === 3) {
                if (buttonNumber === 1) {
                    engine.setValue(group, "beatlooproll_0.125_activate", 1);
                }
                if (buttonNumber === 2) {
                    engine.setValue(group, "beatlooproll_0.25_activate", 1);
                } else if (buttonNumber === 3) {
                    engine.setValue(group, "beatlooproll_0.5_activate", 1);
                }
            }
            // Beat Jump
            if (CDJ100X.currentMode === 4) {
                if (buttonNumber === 1) {
                    engine.setValue(group, "beatjump_" + CDJ100X.BeatJumpRanges[CDJ100X.currentBeatJumpRange] + "_backward", 1);
                }
                if (buttonNumber === 2) {
                    engine.setValue(group, "beatjump_" + CDJ100X.BeatJumpRanges[CDJ100X.currentBeatJumpRange] + "_forward", 1);
                } else if (buttonNumber === 3) {
                    CDJ100X.currentBeatJumpRange++;
                    if (CDJ100X.currentBeatJumpRange >= CDJ100X.BeatJumpRanges.length) {
                        CDJ100X.currentBeatJumpRange = 0;
                    }
                    engine.setValue(group, "beatjump_size", CDJ100X.BeatJumpRanges[CDJ100X.currentBeatJumpRange]);
                }
            }
            // Key Shift
            if (CDJ100X.currentMode === 5) {
                if (buttonNumber === 1) {
                    engine.setValue(group, "pitch_down", 1);
                }
                if (buttonNumber === 2) {
                    engine.setValue(group, "pitch_up", 1);
                } else if (buttonNumber === 3) {
                    engine.setValue(group, "reset_key", 1);
                }
            }
        }
        // Release (needed for Loop Roll to stop)
        else if (value === 0) {
            if (CDJ100X.currentMode === 3) {
                if (buttonNumber === 1) {
                    engine.setValue(group, "beatlooproll_0.125_activate", 0);
                }
                if (buttonNumber === 2) {
                    engine.setValue(group, "beatlooproll_0.25_activate", 0);
                } else if (buttonNumber === 3) {
                    engine.setValue(group, "beatlooproll_0.5_activate", 0);
                }
            }
        }
    };
};

CDJ100X.button1 = CDJ100X.button(1);
CDJ100X.button2 = CDJ100X.button(2);
CDJ100X.button3 = CDJ100X.button(3);

// --- Cue Button ---

CDJ100X.cue = function (channel, control, value, status, group) {
    if (value === 127) {
        if (CDJ100X.shiftPressed) {
            engine.setValue(group, "start_stop", 1);
        } else {
            engine.setValue(group, "cue_cdj", 1);
        }
    } else {
        engine.setValue(group, "cue_cdj", 0);
    }
};

// --- Pitch Slider (14-bit) ---

CDJ100X.pitchMSB = 0;
CDJ100X.pitchLSB = 0;

CDJ100X.pitch = function (channel, control, value, status, group) {
    if (control === 0) {
        CDJ100X.pitchMSB = value;
    } else if (control === 32) {
        CDJ100X.pitchLSB = value;
    }

    var full = (CDJ100X.pitchMSB << 7) | CDJ100X.pitchLSB; // 0-16383
    var normalized = -(full - 8192) / 8192; // -1.0 to +1.0
    engine.setValue(group, "rate", normalized);
};

// --- Browse Encoder ---

CDJ100X.browseDown = function (channel, control, value, status, group) {
    if (value === 127) {
        var currentTab = engine.getValue("[Tab]", "current");
        if (currentTab === 0) {
            engine.setValue("[Channel1]", "waveform_zoom_down", 1);
        }
        engine.setValue("[Library]", "MoveDown", 1);
    }
};

CDJ100X.browseUp = function (channel, control, value, status, group) {
    if (value === 127) {
        var currentTab = engine.getValue("[Tab]", "current");
        if (currentTab === 0) {
            engine.setValue("[Channel1]", "waveform_zoom_up", 1);
        }
        engine.setValue("[Library]", "MoveUp", 1);
    }
};

// --- Load Track ---

CDJ100X.loadTrack = function (channel, control, value, status, group) {
    if (value === 127) {
        var currentTab = engine.getValue("[Tab]", "current");
        var currentLibrary = engine.getValue("[Sidebar]", "sidebar_visible");
        if (currentTab === 1 && currentLibrary === 0) {
            engine.setValue(group, "LoadSelectedTrack", 1);
            engine.setValue("[Tab]", "current", 0);
        }
        if (currentTab === 1 && currentLibrary === 1) {
            engine.setValue("[Sidebar]", "sidebar_visible", 0);
            engine.setValue("[Library]", "GoToItem", 2);
        }
    }
};

// --- Back Button ---

CDJ100X.backButton = function (channel, control, value, status, group) {
    if (value === 127) {
        var currentTab = engine.getValue("[Tab]", "current");
        var currentLibrary = engine.getValue("[Sidebar]", "sidebar_visible");
        if (currentTab === 0) {
            engine.setValue("[Tab]", "current", 1);
            engine.setValue("[Library]", "focused_widget", 3);
        }
        if (currentTab === 1 && currentLibrary === 0) {
            engine.setValue("[Sidebar]", "sidebar_visible", 1);
            engine.setValue("[Library]", "focused_widget", 2);
        }
        if (currentTab === 1 && currentLibrary === 1) {
            engine.setValue("[Sidebar]", "sidebar_visible", 0);
            engine.setValue("[Library]", "focused_widget", 3);
        }
    }
};
