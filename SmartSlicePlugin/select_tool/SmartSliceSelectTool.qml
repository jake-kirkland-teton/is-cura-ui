import QtQuick 2.4
import QtQuick.Controls 1.2
import QtQuick.Layouts 1.1
import QtQuick.Controls.Styles 1.4

import UM 1.2 as UM
import Cura 1.0 as Cura

import SmartSlice 1.0  as SmartSlice

Item {
    id: constraintsTooltip
    width: selectAnchorButton.width * 3 - 2*UM.Theme.getSize("default_margin").width
    height: {
        if (selectAnchorButton.checked) {
            return selectAnchorButton.height + UM.Theme.getSize("default_margin").width + bcListAnchors.height
        }
        if (selectLoadButton.checked) {
            return selectLoadButton.height + UM.Theme.getSize("default_margin").width + bcListForces.height
        }
    }

    UM.I18nCatalog {
        id: catalog;
        name: "smartslice"
    }

    Component.onCompleted: {
        selectAnchorButton.checked = UM.ActiveTool.properties.getValue("AnchorSelectionActive")
        selectLoadButton.checked = UM.ActiveTool.properties.getValue("LoadSelectionActive")
    }

    MouseArea {

        propagateComposedEvents: false
        anchors.fill: parent

        Button
        {
            id: selectAnchorButton

            anchors.left: parent.left
            z: 2

            text: catalog.i18nc("@action:button", "Anchor (Mount)")
            iconSource: "./media/anchor_icon.svg"
            property bool needBorder: true

            style: UM.Theme.styles.tool_button;

            onClicked: {
                UM.ActiveTool.triggerAction("setAnchorSelection");
                selectAnchorButton.checked = true;
                selectLoadButton.checked = false;
                bcListForces.model.loadMagnitude = textLoadDialogMagnitude.text;
            }
        }

        Button {
            id: selectLoadButton
            anchors.left: selectAnchorButton.right;
            anchors.leftMargin: UM.Theme.getSize("default_margin").width;
            z: 1

            text: catalog.i18nc("@action:button", "Load (Directed force)")
            iconSource: "./media/load_icon.svg"
            property bool needBorder: true

            style: UM.Theme.styles.tool_button;

            onClicked: {
                UM.ActiveTool.triggerAction("setLoadSelection");
                selectAnchorButton.checked = false;
                selectLoadButton.checked = true;
            }
        }

        SmartSlice.BoundaryConditionList {
            id: bcListAnchors
            visible: selectAnchorButton.checked
            boundaryConditionType: 0

            anchors.left: selectAnchorButton.left
            anchors.top: selectAnchorButton.bottom
        }

        SmartSlice.BoundaryConditionList {
            id: bcListForces
            visible: selectLoadButton.checked
            boundaryConditionType: 1

            anchors.left: selectAnchorButton.left
            anchors.top: selectAnchorButton.bottom

            onSelectionChanged: {
                checkboxLoadDialogFlipDirection.checked = model.loadDirection;
                textLoadDialogMagnitude.text = model.loadMagnitude;
            }
        }
    }

    Item {
        id: applyLoadDialog

        visible: (selectLoadButton.checked) ? true : false

        width: UM.Theme.getSize("action_panel_widget").width / 2 + 2 * UM.Theme.getSize("default_margin").width
        height: childrenRect.height

        property var handler: SmartSlice.Cloud.loadDialog

        property int xStart: constraintsTooltip.x + selectAnchorButton.width
        property int yStart: constraintsTooltip.y - 18 * UM.Theme.getSize("default_margin").height

        property bool positionSet: handler.positionSet
        property int xPosition: handler.xPosition
        property int yPosition: handler.yPosition

        property Component tickmarks: Repeater {
            id: repeater
            model: control.stepSize > 0 ? 1 + (control.maximumValue - control.minimumValue) / control.stepSize : 0
            Rectangle {
                color: "#777"
                width: 1 ; height: 3
                y: repeater.height
                x: styleData.handleWidth / 2 + index * ((repeater.width - styleData.handleWidth) / (repeater.count-1))
            }
        }

        x: {
            if (handler.positionSet) {
                return xPosition
            }
            return xStart
        }

        y: {
            if (handler.positionSet) {
                return yPosition
            }
            return yStart
        }

        z: 3 //-> A hack to get this on the top

        function trySetPosition(posNewX, posNewY)
        {
            var margin = UM.Theme.getSize("narrow_margin");
            var minPt = base.mapFromItem(null, margin.width, margin.height);
            var maxPt = base.mapFromItem(null,
                CuraApplication.appWidth() - (2 * applyLoadDialog.width),
                CuraApplication.appHeight() - (2 * applyLoadDialog.height)
            );
            var initialY = minPt.y + 100 * screenScaleFactor
            var finalY = maxPt.y - 200 * screenScaleFactor

            applyLoadDialog.x = Math.max(minPt.x, Math.min(maxPt.x, posNewX));
            applyLoadDialog.y = Math.max(initialY, Math.min(finalY, posNewY));

            applyLoadDialog.handler.setPosition(applyLoadDialog.x, applyLoadDialog.y)
        }

        Column {
            id: loadColumn

            anchors.fill: parent

            MouseArea {
                cursorShape: Qt.SizeAllCursor

                height: topDragArea.height
                width: parent.width

                property var clickPos: Qt.point(0, 0)
                property bool dragging: false
                // property int absoluteMinimumHeight: 200 * screenScaleFactor

                onPressed: {
                    clickPos = Qt.point(mouse.x, mouse.y);
                    dragging = true
                }
                onPositionChanged: {
                    if(dragging) {
                        var delta = Qt.point(mouse.x - clickPos.x, mouse.y - clickPos.y);
                        if (delta.x !== 0 || delta.y !== 0) {
                            applyLoadDialog.trySetPosition(applyLoadDialog.x + delta.x, applyLoadDialog.y + delta.y);
                        }
                    }
                }
                onReleased: {
                    dragging = false
                }
                onDoubleClicked: {
                    dragging = false
                    applyLoadDialog.x = applyLoadDialog.xStart
                    applyLoadDialog.y = applyLoadDialog.yStart
                    applyLoadDialog.handler.setPosition(applyLoadDialog.x, applyLoadDialog.y)
                }

                Rectangle {
                    id: topDragArea
                    width: parent.width
                    height: UM.Theme.getSize("narrow_margin").height
                    color: "transparent"
                }
            }

            Rectangle {

                id: contentRectangle

                color: UM.Theme.getColor("main_background")
                border.width: UM.Theme.getSize("default_lining").width
                border.color: UM.Theme.getColor("lining")
                radius: UM.Theme.getSize("default_radius").width

                height: childrenRect.height
                width: parent.width

                Column {
                    id: contentColumn

                    width: parent.width
                    height: childrenRect.height + 2 * UM.Theme.getSize("default_margin").width

                    anchors.top: parent.top

                    anchors.topMargin: UM.Theme.getSize("default_margin").width
                    anchors.bottomMargin: UM.Theme.getSize("default_margin").width/2

                    spacing: UM.Theme.getSize("default_margin").width

                    Row {
                        anchors.left: parent.left
                        anchors.topMargin: UM.Theme.getSize("default_margin").width
                        anchors.leftMargin: UM.Theme.getSize("default_margin").width

                        width: childrenRect.width
                        height: childrenRect.height

                        spacing: UM.Theme.getSize("default_margin").width

                        Label {
                            id: labelLoadDialogType

                            height: parent.height
                            verticalAlignment: Text.AlignVCenter

                            font.bold: true

                            text: "Type:"
                        }

                        ComboBox {
                            id: comboLoadDialogType

                            style: UM.Theme.styles.combobox

                            width: UM.Theme.getSize("action_panel_widget").width / 3
                            anchors.verticalCenter: parent.verticalCenter

                            model: ["Push / Pull"]
                        }
                    }

                    CheckBox {
                        id: checkboxLoadDialogFlipDirection

                        anchors.left: parent.left
                        anchors.leftMargin: 2 * UM.Theme.getSize("default_margin").width

                        text: "Flip Direction"

                        checked: bcListForces.model.loadDirection
                        onCheckedChanged: {
                            bcListForces.model.loadDirection = checked
                        }
                    }

                    Label {
                        id: labelLoadDialogMagnitude

                        anchors.left: parent.left
                        anchors.leftMargin: UM.Theme.getSize("default_margin").width

                        font.bold: true

                        text: "Magnitude:"
                    }

                    TextField {
                        id: textLoadDialogMagnitude
                        style: UM.Theme.styles.text_field

                        function loadHelperStep(value){
                            if (value > 0 && value <= 250) return value * 2.4
                            if (value > 250 && value <= 500) return value * 1.2 + 300
                            if (value > 500 && value <= 1500) return value * .6 + 600
                            else return value
                        }

                        anchors.left: parent.left
                        anchors.leftMargin: 2 * UM.Theme.getSize("default_margin").width

                        onTextChanged: {
                            var value = parseFloat(text)
                            if (value >= 0.0) {
                                bcListForces.model.loadMagnitude = text;
                                loadHelper.value = loadHelperStep(text)
                            }
                        }

                        onEditingFinished: {
                            bcListForces.model.loadMagnitude = text;
                        }

                        validator: DoubleValidator {bottom: 0.0}
                        inputMethodHints: Qt.ImhFormattedNumbersOnly
                        text:  bcListForces.model.loadMagnitude

                        property string unit: "[N]";
                    }


                    Rectangle {
                        id: sliderArea
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: textLoadDialogMagnitude.bottom
                        anchors.topMargin: UM.Theme.getSize("default_margin").width

                        Slider {
                            id: loadHelper
    //                        value:  loadHelperStep(textLoadDialogMagnitude.text)
                            minimumValue: 0
                            maximumValue: 1500
                            stepSize: 1
                            tickmarksEnabled: true
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.rightMargin: UM.Theme.getSize("default_margin").width
                            anchors.leftMargin: UM.Theme.getSize("default_margin").width
                            implicitWidth: parent.width*.85
                            updateValueWhileDragging: false

                            style: SliderStyle {
                                handle: Rectangle
                                {
                                    id: handleButton
                                    color: control.enabled ? UM.Theme.getColor("primary") : UM.Theme.getColor("quality_slider_unavailable")
                                    implicitWidth: UM.Theme.getSize("print_setup_slider_handle").width
                                    implicitHeight: implicitWidth
                                    radius: Math.round(implicitWidth)

                                }
                                groove: Item
                                {
                                    Rectangle
                                    {
                                        height: UM.Theme.getSize("print_setup_slider_groove").height
                                        width: control.width - UM.Theme.getSize("print_setup_slider_handle").width
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        anchors.verticalCenter: parent.verticalCenter
                                        color: control.enabled ? UM.Theme.getColor("quality_slider_available") : UM.Theme.getColor("quality_slider_unavailable")
                                    }
                                }
                                tickmarks: Repeater
                                {
                                    id: repeater
                                    model: control.maximumValue / control.stepSize + 1

                                    Rectangle
                                    {
                                        color: control.enabled ? UM.Theme.getColor("quality_slider_available") : UM.Theme.getColor("quality_slider_unavailable")
                                        implicitWidth: UM.Theme.getSize("print_setup_slider_tickmarks").width
                                        implicitHeight: UM.Theme.getSize("print_setup_slider_tickmarks").height
                                        anchors.verticalCenter: parent.verticalCenter

                                        // Do not use Math.round otherwise the tickmarks won't be aligned
                                        x: ((styleData.handleWidth / 2) - (implicitWidth / 2) + (index * ((repeater.width - styleData.handleWidth) / (repeater.count-1))))
                                        radius: Math.round(implicitWidth / 2)
                                        visible: (index % 300) == 0 // Only show steps of 10%
                                    }
                                }
                            }
                            onValueChanged:
                            {
                                function loadMagnitudeStep(value){
                                    if (value === 0) {return 0}
                                    else if (value === 600 || value === 300) {return value / 2.4}
                                    else if (value === 900) {return value / 1.8 }
                                    else if (value === 1200) {return value / 1.2}
                                    else if (value === 1500) {return 1500}
                                }
    //                          simulate step size of 300
                                var roundedSliderValue = Math.round(loadHelper.value / 300) * 300
                                if (loadHelper.pressed === true || loadHelper.hovered == true){
                                    textLoadDialogMagnitude.text = loadMagnitudeStep(roundedSliderValue)
                                    loadHelper.value = roundedSliderValue
                                }
                            }
                        }
                    }
                }
                Rectangle{

                    function isVis(){
                        if (loadHelper.value === 300) return true
                        else if (loadHelper.value === 600) return true
                        else if (loadHelper.value === 900) return true
                        else if (loadHelper.value === 1200) return true
                        else return false
                    }

                    color: UM.Theme.getColor("main_background")
                    border.width: UM.Theme.getSize("default_lining").width
                    border.color: UM.Theme.getColor("lining")
                    anchors.left: contentColumn.right
                    anchors.leftMargin: UM.Theme.getSize("default_margin").width
                    radius: UM.Theme.getSize("default_radius").width

                    height: contentColumn.height + UM.Theme.getSize("default_margin").width*2
                    width: contentColumn.width

                    anchors.top: contentColumn.top
                    anchors.topMargin: -UM.Theme.getSize("default_margin").width
                    visible: isVis()

                    Label{
                        id: topText
                        anchors.top:parent.top
                        anchors.topMargin: UM.Theme.getSize("default_margin").width
                        anchors.left:parent.left
                        anchors.leftMargin: UM.Theme.getSize("default_margin").width
                        renderType: Text.NativeRendering
                        font: UM.Theme.getFont("default")
                        text: "<b>Example:</b>"
                    }

                    Image{
                        id: loadHelperImage
                        anchors.top: topText.bottom
                        anchors.right:parent.right
                        anchors.rightMargin: UM.Theme.getSize("default_margin").width
                        anchors.left: parent.left
                        anchors.leftMargin: UM.Theme.getSize("default_margin").width
                        anchors.bottom:loadHelperSeparator.top
                        smooth: true
                        fillMode: Image.PreserveAspectFit

                        source:image()
                        function image(){
                            if (loadHelper.value === 300) return "media/Toddler.jpg"
                            else if (loadHelper.value === 600)return "media/Child.jpg"
                            else if (loadHelper.value === 900) return "media/Teenager.jpg"
                            else if (loadHelper.value === 1200) return "media/Adult.jpg"
                            else return ""
                        }
                    }

                    Rectangle {
                        id: loadHelperSeparator
                        border.color: UM.Theme.getColor("lining")
                        color: UM.Theme.getColor("lining")
                        anchors.bottom: imageType.top
                        anchors.bottomMargin: UM.Theme.getSize("default_margin").width/2
                        anchors.right: parent.right
                        anchors.left: parent.left
                        width: parent.width
                        height: 1

                    }

                    Text {
                        id: imageType
                        function getTextType(){
                            if (loadHelper.value === 300) return "<b>Toddler </b>"
                            else if (loadHelper.value === 600) return "<b>Young Child</b>"
                            else if (loadHelper.value === 900) return "<b>Teenager </b>"
                            else if (loadHelper.value === 1200) return "<b>Adult </b>"
                            else return ""
                        }
//                        anchors.top:loadHelperSeparator.bottom
                        anchors.bottom: weight.top
                        anchors.topMargin: UM.Theme.getSize("default_margin").width/2
                        anchors.left: parent.left
                        anchors.leftMargin: UM.Theme.getSize("default_margin").width
                        font: UM.Theme.getFont("default");
                        renderType: Text.NativeRendering
                        text: getTextType()
                    }
                    Text{
                        id: weight
                        function getTextType(){
                            if (loadHelper.value === 300) return "125 N (~30 lbs)"
                            else if (loadHelper.value === 600) return "250 N (~60 lbs)"
                            else if (loadHelper.value === 900) return "500 N (~110 lbs)"
                            else if (loadHelper.value === 1200) return "1000 N (~225 lbs)"
                            else return ""
                        }
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: UM.Theme.getSize("default_margin").width/2

                        anchors.topMargin: UM.Theme.getSize("default_margin").width/2
                        anchors.left: parent.left
                        anchors.leftMargin: UM.Theme.getSize("default_margin").width
                        font: UM.Theme.getFont("default");
                        renderType: Text.NativeRendering
                        text: getTextType()
                    }
                }
            }
        }
    }
}

