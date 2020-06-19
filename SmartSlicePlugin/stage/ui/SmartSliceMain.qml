/*
    SmartSliceMain.qml
    Teton Simulation
    Last Modified October 16, 2019
*/

/*
    Contains definitions for Smart Slice's main structural UI elements

    This includes: (Vert. Horiz.)
        *  Brand Logo (Bottom Middle)
        *  "Smart Slice" Button (Bottom Right)
*/


//  API Imports
import QtQuick 2.7
import QtQuick.Controls 2.2
import QtQuick.Layouts 1.3
import QtQuick.Controls.Styles 1.1
import QtGraphicalEffects 1.0

import UM 1.2 as UM
import Cura 1.0 as Cura
import SmartSlice 1.0 as SmartSlice

//  Main UI Stage Components
Item {
    id: smartSliceMain

    //  Main Stage Accessible Properties
    property int smartLoads : 0
    property int smartAnchors : 0

    //  1.) Brand Logo
    Image {
        id: tetonBranding
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.leftMargin: UM.Theme.getSize("thick_margin").width
        anchors.bottomMargin: UM.Theme.getSize("thick_margin").height

        width: 250
        fillMode: Image.PreserveAspectFit
        source: "../images/branding.png"
        mipmap: true
    }

    //  2.) Smart Slice window which holds all of the controls for validate / optimize, and results viewing
    //      This is basically the same thing as ActionPanelWidget in Cura
    Rectangle {
        id: smartSliceWindow //    TODO: Change to Widget when everything works

        width: UM.Theme.getSize("action_panel_widget").width
        height: mainColumn.height + 2 * UM.Theme.getSize("thick_margin").height

        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: UM.Theme.getSize("thick_margin").width
        anchors.bottomMargin: UM.Theme.getSize("thick_margin").height

        color: UM.Theme.getColor("main_background")
        border.width: UM.Theme.getSize("default_lining").width
        border.color: UM.Theme.getColor("lining")
        radius: UM.Theme.getSize("default_radius").width

        // A single column to hold all of our objects
        Column {
            id: mainColumn

            width: parent.width
            spacing: UM.Theme.getSize("thin_margin").height

            anchors {
                left: parent.left
                right: parent.right
                bottom: parent.bottom
                rightMargin: UM.Theme.getSize("thick_margin").width
                leftMargin: UM.Theme.getSize("thick_margin").width
                bottomMargin: UM.Theme.getSize("thick_margin").height
                topMargin: UM.Theme.getSize("thick_margin").height
            }

            // The first row of the column, which holds the status messages and info icons
            RowLayout {
                width: parent.width

                // First column of the row holding the status messages
                Column {
                    Layout.fillWidth: true

                    spacing: UM.Theme.getSize("thin_margin").height

                    // Main status message
                    Label {
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        font: SmartSlice.Cloud.isValidated ? UM.Theme.getFont("medium_bold") : UM.Theme.getFont("default")
                        renderType: Text.NativeRendering

                        text: SmartSlice.Cloud.sliceStatus
                    }

                    // Secondary status message with hint
                    Label {
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        font: UM.Theme.getFont("default")
                        renderType: Text.NativeRendering

                        text: SmartSlice.Cloud.sliceHint
                    }

                    // Optimized message
                    Cura.IconWithText {
                        id: estimatedTime
                        width: parent.width

                        text: Qt.formatTime(SmartSlice.Cloud.resultTimeTotal, "h") + " hours " + Qt.formatTime(SmartSlice.Cloud.resultTimeTotal, "m") + " minutes"
                        source: UM.Theme.getIcon("clock")
                        font: UM.Theme.getFont("medium_bold")

                        visible: SmartSlice.Cloud.isOptimized
                    }

                    Cura.IconWithText {
                        id: estimatedCosts
                        width: parent.width

                        text: {
                            var totalLengths = 0
                            var totalWeights = 0
                            var totalCosts = 0.0
                            if (SmartSlice.Cloud.materialLength > 0) {
                                totalLengths = SmartSlice.Cloud.materialLength
                                totalWeights = SmartSlice.Cloud.materialWeight.toFixed(2)
                                totalCosts = SmartSlice.Cloud.materialCost.toFixed(2)
                            }
                            if(totalCosts > 0)
                            {
                                var costString = "%1 %2".arg(UM.Preferences.getValue("cura/currency")).arg(totalCosts)
                                return totalWeights + "g · " + totalLengths.toFixed(2) + "m · " + costString
                            }
                            return totalWeights + "g · " + totalLengths.toFixed(2) + "m"
                        }
                        source: UM.Theme.getIcon("spool")
                        font: UM.Theme.getFont("default")

                        visible: SmartSlice.Cloud.isOptimized
                    }
                }

                // Second column in the top row, holding the status indicator
                Column {
                    Layout.alignment: Qt.AlignTop

                    // Status indicator (info image) which has the popup
                    Image {
                        id: smartSliceInfoIcon

                        width: UM.Theme.getSize("section_icon").width
                        height: UM.Theme.getSize("section_icon").height

                        anchors.right: parent.right

                        fillMode: Image.PreserveAspectFit
                        mipmap: true

                        source: SmartSlice.Cloud.sliceIconImage
                        visible: SmartSlice.Cloud.sliceIconVisible

                        Connections {
                            target: SmartSlice.Cloud
                            onSliceIconImageChanged: {
                                smartSliceInfoIcon.source = SmartSlice.Cloud.sliceIconImage
                            }
                            onSliceIconVisibleChanged: {
                                smartSliceInfoIcon.visible = SmartSlice.Cloud.sliceIconVisible
                            }
                            onSliceInfoOpenChanged: {
                                if (SmartSlice.Cloud.sliceInfoOpen) {
                                    smartSlicePopup.open()
                                }
                            }
                        }

                        MouseArea
                        {
                            anchors.fill: parent
                            hoverEnabled: true
                            onEntered: {
                                if (visible) {
                                    smartSlicePopup.open();
                                }
                            }
                            onExited: smartSlicePopup.close()
                        }

                        // Popup message with slice results
                        Popup {
                            id: smartSlicePopup

                            y: -(height + UM.Theme.getSize("default_arrow").height + UM.Theme.getSize("thin_margin").height)
                            x: parent.width - width + UM.Theme.getSize("thin_margin").width

                            contentWidth: UM.Theme.getSize("action_panel_information_widget").width
                            contentHeight: smartSlicePopupContents.height

                            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

                            opacity: opened ? 1 : 0
                            Behavior on opacity { NumberAnimation { duration: 100 } }

                            Column {
                                id: smartSlicePopupContents

                                width: parent.width

                                spacing: UM.Theme.getSize("default_margin").width

                                property var header_font: UM.Theme.getFont("default_bold")
                                property var header_color: UM.Theme.getColor("primary")
                                property var subheader_font: UM.Theme.getFont("default")
                                property var subheader_color: "#A9A9A9"
                                property var description_font: UM.Theme.getFont("default")
                                property var description_color: UM.Theme.getColor("text")
                                property var value_font: UM.Theme.getFont("default")
                                property var value_color: UM.Theme.getColor("text")

                                property color warningColor: "#F3BA1A"
                                property color errorColor: "#F15F63"
                                property color successColor: "#5DBA47"

                                property var col1_width: 0.45
                                property var col2_width: 0.3
                                property var col3_width: 0.25

                                Column {
                                    id: requirements

                                    width: parent.width
                                    topPadding: UM.Theme.getSize("default_margin").height
                                    leftPadding: UM.Theme.getSize("default_margin").width
                                    rightPadding: UM.Theme.getSize("default_margin").width

                                    /* REQUIREMENTS HEADER */
                                    Label {
                                        font: smartSlicePopupContents.header_font
                                        color: smartSlicePopupContents.header_color
                                        renderType: Text.NativeRendering

                                        text: "REQUIREMENTS"
                                    }

                                    Row {
                                        id: layoutRequirements
                                        width: parent.width

                                        Column {
                                            width: smartSlicePopupContents.col1_width * (parent.width - 2 * UM.Theme.getSize("default_margin").width)

                                            Label {
                                                width: parent.width
                                                bottomPadding: UM.Theme.getSize("thin_margin").height

                                                font: smartSlicePopupContents.subheader_font
                                                color: smartSlicePopupContents.subheader_color

                                                text: "Objective"
                                            }
                                            Label {
                                                id: labelDescriptionSafetyFactor

                                                width: parent.width

                                                font: smartSlicePopupContents.description_font
                                                color: SmartSlice.Cloud.safetyFactorColor
                                                renderType: Text.NativeRendering
                                                textFormat: Text.RichText

                                                text: "Factor of Safety:"
                                            }
                                            Label {
                                                id: labelDescriptionMaximumDisplacement

                                                width: parent.width

                                                font: smartSlicePopupContents.description_font
                                                color: SmartSlice.Cloud.maxDisplaceColor
                                                renderType: Text.NativeRendering
                                                textFormat: Text.RichText

                                                text: "Max Displacement:"
                                            }
                                        }
                                        Column {
                                            id: secondColumnPopup
                                            width: smartSlicePopupContents.col2_width * (parent.width - 2 * UM.Theme.getSize("default_margin").width)

                                            Label {
                                                width: parent.width
                                                bottomPadding: UM.Theme.getSize("thin_margin").height

                                                horizontalAlignment: Text.AlignHCenter
                                                font: smartSlicePopupContents.subheader_font
                                                color: smartSlicePopupContents.subheader_color

                                                text: "Computed"
                                            }
                                            Label {
                                                id: labelResultSafetyFactor
                                                width: parent.width

                                                horizontalAlignment: Text.AlignHCenter
                                                font: smartSlicePopupContents.value_font
                                                color: SmartSlice.Cloud.safetyFactorColor
                                                renderType: Text.NativeRendering
                                                textFormat: Text.RichText

                                                Connections {
                                                    target: SmartSlice.Cloud
                                                    onResultSafetyFactorChanged: {
                                                        labelResultSafetyFactor.text = parseFloat(Math.round(SmartSlice.Cloud.resultSafetyFactor * 1000) / 1000).toFixed(1)
                                                    }
                                                }

                                                text: parseFloat(Math.round(SmartSlice.Cloud.resultSafetyFactor * 1000) / 1000).toFixed(1)
                                            }
                                            Label {
                                                id: labelResultMaximalDisplacement

                                                width: parent.width

                                                horizontalAlignment: Text.AlignHCenter
                                                font: smartSlicePopupContents.value_font
                                                color: SmartSlice.Cloud.maxDisplaceColor
                                                renderType: Text.NativeRendering
                                                textFormat: Text.RichText

                                                Connections {
                                                    target: SmartSlice.Cloud
                                                    onResultMaximalDisplacementChanged: {
                                                        labelResultMaximalDisplacement.text = parseFloat(Math.round(SmartSlice.Cloud.resultMaximalDisplacement * 1000) / 1000).toFixed(2)
                                                    }
                                                }

                                                text: parseFloat(Math.round(SmartSlice.Cloud.resultMaximalDisplacement * 1000) / 1000).toFixed(2)
                                            }
                                        }
                                        Column {
                                            id: thirdColumnPopup
                                            width: smartSlicePopupContents.col3_width * (parent.width - 2 * UM.Theme.getSize("default_margin").width)

                                            Label {
                                                width: parent.width
                                                bottomPadding: UM.Theme.getSize("thin_margin").height

                                                horizontalAlignment: Text.AlignRight
                                                font: smartSlicePopupContents.subheader_font
                                                color: smartSlicePopupContents.subheader_color

                                                text: "Target"
                                            }
                                            Label {
                                                id: labelTargetSafetyFactor

                                                width: parent.width

                                                horizontalAlignment: Text.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: SmartSlice.Cloud.safetyFactorColor
                                                renderType: Text.NativeRendering
                                                textFormat: Text.RichText

                                                Connections {
                                                    target: SmartSlice.Cloud
                                                    onTargetSafetyFactorChanged: {
                                                        labelTargetSafetyFactor.text = parseFloat(Math.round(SmartSlice.Cloud.targetSafetyFactor * 1000) / 1000).toFixed(1)
                                                    }
                                                }

                                                text: parseFloat(Math.round(SmartSlice.Cloud.targetSafetyFactor * 1000) / 1000).toFixed(1)
                                            }
                                            Label {
                                                id: labelTargetMaximalDisplacement

                                                width: parent.width

                                                horizontalAlignment: Text.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: SmartSlice.Cloud.maxDisplaceColor
                                                renderType: Text.NativeRendering
                                                textFormat: Text.RichText

                                                Connections {
                                                    target: SmartSlice.Cloud
                                                    onTargetMaximalDisplacementChanged: {
                                                        labelTargetMaximalDisplacement.text = parseFloat(Math.round(SmartSlice.Cloud.targetMaximalDisplacement * 1000) / 1000).toFixed(2)
                                                    }
                                                }

                                                text: parseFloat(Math.round(SmartSlice.Cloud.targetMaximalDisplacement * 1000) / 1000).toFixed(2)
                                            }
                                        }
                                    }
                                }


                                /* TIME ESTIMATION HEADER */
                                Column {
                                    id: timeEstimation

                                    width: parent.width
                                    leftPadding: UM.Theme.getSize("default_margin").width
                                    rightPadding: UM.Theme.getSize("default_margin").width

                                    Label {
                                        font: smartSlicePopupContents.header_font
                                        color: smartSlicePopupContents.header_color

                                        text: "TIME ESTIMATION"
                                    }

                                    Row {
                                        width: parent.width

                                        Column {
                                            width: smartSlicePopupContents.col1_width * (parent.width - 2 * UM.Theme.getSize("default_margin").width)

                                            Label {
                                                text: "Print time:"

                                                width: parent.width

                                                Layout.alignment: Qt.AlignRight
                                                font: smartSlicePopupContents.description_font
                                                color: smartSlicePopupContents.description_color
                                                renderType: Text.NativeRendering
                                                textFormat: Text.RichText
                                            }
                                            /*
                                            Label {
                                                Layout.fillWidth: true

                                                text: "Infill:"

                                                font: smartSlicePopupContents.description_font
                                                color: smartSlicePopupContents.description_color
                                            }
                                            Label {
                                                text: "Inner Walls:"

                                                font: smartSlicePopupContents.description_font
                                                color: smartSlicePopupContents.description_color
                                            }
                                            Label {
                                                text: "Outer Walls:"

                                                font: smartSlicePopupContents.description_font
                                                color: smartSlicePopupContents.description_color
                                            }
                                            Label {
                                                text: "Retractions:"

                                                font: smartSlicePopupContents.description_font
                                                color: smartSlicePopupContents.description_color
                                            }
                                            Label {
                                                font: smartSlicePopupContents.description_font
                                                color: smartSlicePopupContents.description_color

                                                text: "Skin:"
                                            }
                                            Label {
                                                font: smartSlicePopupContents.description_font
                                                color: smartSlicePopupContents.description_color

                                                text: "Skirt:"
                                            }
                                            Label {
                                                font: smartSlicePopupContents.description_font
                                                color: smartSlicePopupContents.description_color

                                                text: "Travel:"
                                            }
                                            */
                                        }

                                        Column {
                                            width: smartSlicePopupContents.col2_width * (parent.width - 2 * UM.Theme.getSize("default_margin").width)

                                            Label {

                                                width: parent.width

                                                horizontalAlignment: Text.AlignHCenter
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color
                                                renderType: Text.NativeRendering
                                                textFormat: Text.RichText

                                                text: Qt.formatTime(SmartSlice.Cloud.resultTimeTotal, "hh:mm")
                                            }
                                            /*
                                            Label {
                                                Layout.alignment: Qt.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color

                                                text: Qt.formatTime(SmartSlice.Cloud.resultTimeInfill, "hh:mm")
                                            }
                                            Label {
                                                Layout.alignment: Qt.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color

                                                text: Qt.formatTime(SmartSlice.Cloud.resultTimeInnerWalls, "hh:mm")
                                            }
                                            Label {
                                                Layout.alignment: Qt.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color

                                                text: Qt.formatTime(SmartSlice.Cloud.resultTimeOuterWalls, "hh:mm")
                                            }
                                            Label {
                                                Layout.alignment: Qt.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color

                                                text: Qt.formatTime(SmartSlice.Cloud.resultTimeRetractions, "hh:mm")
                                            }
                                            Label {
                                                Layout.alignment: Qt.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color

                                                text: Qt.formatTime(SmartSlice.Cloud.resultTimeSkin, "hh:mm")
                                            }
                                            Label {
                                                Layout.alignment: Qt.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color

                                                text: Qt.formatTime(SmartSlice.Cloud.resultTimeSkirt, "hh:mm")
                                            }
                                            Label {
                                                Layout.alignment: Qt.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color

                                                text: Qt.formatTime(SmartSlice.Cloud.resultTimeTravel, "hh:mm")
                                            }
                                            */
                                        }

                                        Column {
                                            width: smartSlicePopupContents.col3_width * (parent.width - 2 * UM.Theme.getSize("default_margin").width)

                                            Label {

                                                width: parent.width

                                                horizontalAlignment: Text.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color
                                                renderType: Text.NativeRendering
                                                textFormat: Text.RichText

                                                text: "100 %"
                                            }
                                            /*
                                            Label {
                                                Layout.alignment: Qt.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color

                                                text: SmartSlice.Cloud.percentageTimeInfill.toFixed(2) + " %"
                                            }
                                            Label {
                                                Layout.alignment: Qt.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color

                                                text: SmartSlice.Cloud.percentageTimeInnerWalls.toFixed(2) + " %"
                                            }
                                            Label {
                                                Layout.alignment: Qt.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color

                                                text: SmartSlice.Cloud.percentageTimeOuterWalls.toFixed(2) + " %"
                                            }
                                            Label {
                                                Layout.alignment: Qt.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color

                                                text: SmartSlice.Cloud.percentageTimeRetractions.toFixed(2) + " %"
                                            }
                                            Label {
                                                Layout.alignment: Qt.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color

                                                text: SmartSlice.Cloud.percentageTimeSkin.toFixed(2) + " %"
                                            }
                                            Label {
                                                Layout.alignment: Qt.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color

                                                text: SmartSlice.Cloud.percentageTimeSkirt.toFixed(2) + " %"
                                            }
                                            Label {
                                                Layout.alignment: Qt.AlignRight
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color

                                                text: SmartSlice.Cloud.percentageTimeTravel.toFixed(2) + " %"
                                            }
                                            */
                                        }
                                    }
                                }

                                Column {
                                    id: materialEstimate
                                    width: parent.width

                                    leftPadding: UM.Theme.getSize("default_margin").width
                                    rightPadding: UM.Theme.getSize("default_margin").width
                                    bottomPadding: UM.Theme.getSize("default_margin").height

                                    /* Material ESTIMATION HEADER */
                                    Label {
                                        font: smartSlicePopupContents.header_font
                                        color: smartSlicePopupContents.header_color

                                        text: "MATERIAL ESTIMATION"
                                    }

                                    Row {
                                        width: parent.width

                                        Column {
                                            width: 0.4 * (parent.width - 2 * UM.Theme.getSize("default_margin").width)

                                            Label {
                                                width: parent.width

                                                font: smartSlicePopupContents.value_font
                                                renderType: Text.NativeRendering
                                                textFormat: Text.RichText

                                                text: SmartSlice.Cloud.materialName
                                            }
                                        }

                                        Column {
                                            width: 0.2 * (parent.width - 2 * UM.Theme.getSize("default_margin").width)

                                            Label {
                                                width: parent.width

                                                horizontalAlignment: Text.AlignHCenter
                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color
                                                renderType: Text.NativeRendering
                                                textFormat: Text.RichText

                                                text: SmartSlice.Cloud.materialLength + " m"
                                            }
                                        }

                                        Column {
                                            width: 0.2 * (parent.width - 2 * UM.Theme.getSize("default_margin").width)

                                            Label {
                                                width: parent.width

                                                horizontalAlignment: Text.AlignHCenter

                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color
                                                renderType: Text.NativeRendering
                                                textFormat: Text.RichText

                                                text: SmartSlice.Cloud.materialWeight.toFixed(2) + " g"
                                            }
                                        }

                                        Column {
                                            width: 0.2 * (parent.width - 2 * UM.Theme.getSize("default_margin").width)

                                            Label {
                                                width: parent.width

                                                Layout.alignment: Qt.AlignRight
                                                horizontalAlignment: Text.AlignRight

                                                font: smartSlicePopupContents.value_font
                                                color: smartSlicePopupContents.value_color
                                                renderType: Text.NativeRendering
                                                textFormat: Text.RichText

                                                text: SmartSlice.Cloud.materialCost.toFixed(2) + " €"
                                            }
                                        }
                                    }
                                }
                            }


                            background: UM.PointingRectangle
                            {
                                color: UM.Theme.getColor("tool_panel_background")
                                borderColor: UM.Theme.getColor("lining")
                                borderWidth: UM.Theme.getSize("default_lining").width

                                target: Qt.point(width - (smartSliceInfoIcon.width / 2) - UM.Theme.getSize("thin_margin").width,
                                                height + UM.Theme.getSize("default_arrow").height - UM.Theme.getSize("thin_margin").height)

                                arrowSize: UM.Theme.getSize("default_arrow").width
                            }
                        }
                    }
                }
            }

            // Holds all of the buttons and sets the height
            Item {
                id: buttons

                width: parent.width
                height: UM.Theme.getSize("action_button").height

                anchors.bottom: smartSliceWindow.bottom

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: {
                        if (SmartSlice.Cloud.errors && !smartSliceButton.enabled && !smartSliceWarningPopup.opened) {
                            smartSliceWarningPopup.open();
                        }
                    }
                }

                Cura.PrimaryButton {
                    id: smartSliceButton

                    height: parent.height
                    width: smartSliceSecondaryButton.visible ? 2 / 3 * parent.width - 1 / 2 * UM.Theme.getSize("default_margin").width : parent.width
                    fixedWidthMode: true

                    anchors.right: parent.right
                    anchors.bottom: parent.bottom

                    text: SmartSlice.Cloud.sliceButtonText

                    enabled: SmartSlice.Cloud.sliceButtonEnabled
                    visible: SmartSlice.Cloud.sliceButtonVisible

                    Connections {
                        target: SmartSlice.Cloud
                        onSliceButtonEnabledChanged: { smartSliceButton.enabled = SmartSlice.Cloud.sliceButtonEnabled }
                        onSliceButtonFillWidthChanged: { smartSliceButton.Layout.fillWidth = SmartSlice.Cloud.sliceButtonFillWidth }
                    }

                    /*
                        Smart Slice Button Click Event
                    */
                    onClicked: {
                        //  Show Validation Dialog
                        SmartSlice.Cloud.sliceButtonClicked()
                    }
                }

                Glow {
                    anchors.fill: smartSliceButton
                    radius: 8
                    samples: 17
                    color: smartSlicePopupContents.warningColor
                    source: smartSliceButton
                    visible: SmartSlice.Cloud.errors && !smartSliceButton.enabled
                }

                // Popup message with warning / errors
                Popup {
                    id: smartSliceWarningPopup

                    y: -(height + UM.Theme.getSize("default_arrow").height + UM.Theme.getSize("thin_margin").height)
                    x: parent.width - width + UM.Theme.getSize("thin_margin").width

                    contentWidth: parent.width
                    contentHeight: smartSliceWarningContents.height

                    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent | smartSliceButton.enabled

                    opacity: opened ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: 100 } }

                    Column {
                        id: smartSliceWarningContents

                        width: parent.width
                        spacing: UM.Theme.getSize("default_margin").width

                        Column {

                            width: parent.width
                            topPadding: UM.Theme.getSize("default_margin").height
                            leftPadding: UM.Theme.getSize("default_margin").width
                            rightPadding: UM.Theme.getSize("default_margin").width

                            spacing: UM.Theme.getSize("thin_margin").width

                            Label {
                                font: smartSlicePopupContents.header_font
                                color: smartSlicePopupContents.value_color
                                renderType: Text.NativeRendering

                                text: "ITEMS NEED RESOLVED"
                            }

                            Label {
                                font: smartSlicePopupContents.subheader_font
                                color: smartSlicePopupContents.value_color
                                renderType: Text.NativeRendering
                                width: parent.width
                                rightPadding: UM.Theme.getSize("default_margin").width
                                wrapMode: Text.WordWrap
                                text: "The following items need to be resolved before you can validate:"
                            }
                        }

                        ScrollView {
                            property int maxHeight: 14 * UM.Theme.getSize("section_icon").width

                            width: parent.width
                            height: scrollErrors.height > maxHeight ? maxHeight : scrollErrors.height

                            contentWidth: parent.width

                            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                            ScrollBar.vertical.policy: ScrollBar.AsNeeded

                            clip: true

                            Item {
                                id: scrollErrors

                                width: parent.width
                                height: smartSliceErrors.height
                                implicitHeight: height

                                Column {
                                    id: smartSliceErrors

                                    function getErrors() {
                                        var errors = SmartSlice.Cloud.errors
                                        var error_text = []
                                        for(var error in errors) {
                                            var error_resolution = []
                                            error_resolution.push(error)
                                            error_resolution.push(errors[error])

                                            error_text.push(error_resolution)
                                        }
                                        return error_text
                                    }

                                    Repeater {
                                        model: smartSliceErrors.getErrors()

                                        Column {
                                            width: parent.width

                                            leftPadding: UM.Theme.getSize("default_margin").width
                                            rightPadding: UM.Theme.getSize("default_margin").width
                                            spacing: UM.Theme.getSize("thin_margin").width

                                            Row {
                                                width: parent.width

                                                UM.RecolorImage {
                                                    id: error_icon

                                                    width: 0.5 * UM.Theme.getSize("section_icon").width
                                                    height: width
                                                    Layout.fillHeight: true
                                                    anchors.verticalCenter: parent.verticalCenter

                                                    source: "../images/circle.png"
                                                    color: smartSlicePopupContents.warningColor
                                                }

                                                Label {
                                                    id: error_label

                                                    width: parent.width - error_icon.width - 3 * UM.Theme.getSize("default_margin").width - UM.Theme.getSize("thin_margin").width
                                                    anchors. verticalCenter: parent.verticalCenter
                                                    leftPadding: UM.Theme.getSize("thin_margin").width
                                                    rightPadding: UM.Theme.getSize("default_margin").width
                                                    Layout.fillHeight: true

                                                    text: modelData[0]
                                                    font: smartSlicePopupContents.value_font
                                                    color: smartSlicePopupContents.value_color
                                                    wrapMode: Text.WordWrap
                                                    verticalAlignment: Text.AlignVCenter
                                                }
                                            }

                                            Row {
                                                width: parent.width
                                                leftPadding: UM.Theme.getSize("thick_margin").width

                                                UM.RecolorImage {
                                                    id: resolution_icon

                                                    width: 0.5 * UM.Theme.getSize("section_icon").width
                                                    height: width
                                                    Layout.fillHeight: true

                                                    anchors.verticalCenter: parent.verticalCenter

                                                    source: "../images/circle.png"
                                                    color: smartSlicePopupContents.successColor
                                                }

                                                Label {
                                                    id: resolution_label

                                                    width: parent.width - resolution_icon.width - 3 * UM.Theme.getSize("default_margin").width - UM.Theme.getSize("thin_margin").width
                                                    anchors. verticalCenter: parent.verticalCenter
                                                    leftPadding: UM.Theme.getSize("thin_margin").width
                                                    rightPadding: UM.Theme.getSize("default_margin").width
                                                    Layout.fillHeight: true

                                                    text: modelData[1]
                                                    font: smartSlicePopupContents.value_font
                                                    color: smartSlicePopupContents.value_color
                                                    wrapMode: Text.WordWrap
                                                    verticalAlignment: Text.AlignVCenter
                                                }
                                            }
                                        }
                                    }

                                    width: parent.width
                                    topPadding: UM.Theme.getSize("default_margin").height
                                    leftPadding: UM.Theme.getSize("default_margin").width
                                    rightPadding: UM.Theme.getSize("default_margin").width
                                    bottomPadding: UM.Theme.getSize("default_margin").width

                                    spacing: UM.Theme.getSize("thin_margin").width

                                    Connections {
                                        target: SmartSlice.Cloud
                                        onSmartSliceErrorsChanged: {
                                            smartSliceErrors.forceLayout()
                                            smartSliceWarningContents.forceLayout()
                                        }
                                    }
                                }
                            }
                        }
                    }

                    background: UM.PointingRectangle
                    {
                        color: UM.Theme.getColor("tool_panel_background")
                        borderColor: UM.Theme.getColor("lining")
                        borderWidth: UM.Theme.getSize("default_lining").width

                        target: Qt.point(width - (smartSliceSecondaryButton.width / 2) - UM.Theme.getSize("thin_margin").width,
                                        height + UM.Theme.getSize("default_arrow").height - UM.Theme.getSize("thin_margin").height)

                        arrowSize: UM.Theme.getSize("default_arrow").width
                    }

                }

                Cura.SecondaryButton {
                    id: smartSliceSecondaryButton

                    height: parent.height
                    width: smartSliceButton.visible ? (
                        visible ? 1 / 3 * parent.width - 1 / 2 * UM.Theme.getSize("default_margin").width : UM.Theme.getSize("thick_margin").width
                        ) : parent.width
                    fixedWidthMode: true

                    anchors.left: parent.left
                    anchors.bottom: parent.bottom

                    text: SmartSlice.Cloud.secondaryButtonText

                    visible: SmartSlice.Cloud.secondaryButtonVisible

                    Connections {
                        target: SmartSlice.Cloud
                        onSecondaryButtonVisibleChanged: { smartSliceSecondaryButton.visible = SmartSlice.Cloud.secondaryButtonVisible }
                        onSecondaryButtonFillWidthChanged: { smartSliceSecondaryButton.Layout.fillWidth = SmartSlice.Cloud.secondaryButtonFillWidth }
                    }

                    /*
                        Smart Slice Button Click Event
                    */
                    onClicked: {
                        //  Show Validation Dialog
                        SmartSlice.Cloud.secondaryButtonClicked()
                    }
                }
            }
        }
    }

}
