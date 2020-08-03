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
            iconSource: "./anchor_icon.svg"
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
            iconSource: "./load_icon.svg"
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

                height:childrenRect.height
                width: parent.width

                Column {
                    id: contentColumn

                    width: parent.width
                    height: childrenRect.height + 2 * UM.Theme.getSize("default_margin").width

                    anchors.top: parent.top

                    anchors.topMargin: UM.Theme.getSize("default_margin").width
                    anchors.bottomMargin: UM.Theme.getSize("default_margin").width

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

                        anchors.left: parent.left
                        anchors.leftMargin: 2 * UM.Theme.getSize("default_margin").width

                        onTextChanged: {
                            var value = parseFloat(text)
                            if (value >= 0.0) {
                                bcListForces.model.loadMagnitude = text;
                            }
                        }

                        onEditingFinished: {
                            bcListForces.model.loadMagnitude = text;
                        }

                        validator: DoubleValidator {bottom: 0.0}
                        inputMethodHints: Qt.ImhFormattedNumbersOnly

                        property string unit: "[N]";
                    }

                    Binding{
                        function loadMagnitudeStep(value){
                            if (loadHelper.value < 10) return textLoadDialogMagnitude.text
                            if (loadHelper.value >= 10 && loadHelper.value<=600) return Math.floor(loadHelper.value/2.4)
                            if (loadHelper.value >600 && loadHelper.value<=900) return Math.floor(loadHelper.value/1.2 -250)
                            if (loadHelper.value >900 && loadHelper.value<1500) return Math.floor(loadHelper.value/.6 - 1000)
                        }
                        function getVal(){
                            if (loadHelper.value>=10  && loadHelper.value<=1500) return loadMagnitudeStep()
                            else return bcListForces.model.loadMagnitude
                        }
                        target: textLoadDialogMagnitude
                        property:"text"
                        value: getVal()


                    }


                   Slider {

                        function loadHelperStep(value){
                            if (value > 0 && value<=250) return value*2.4
                            if (value >250 && value<=500) return value*1.2+300
                            if (value >500 && value<=1500) return value*.6 +600
                            else return value
                        }

                        id:loadHelper
                        value: loadHelperStep(textLoadDialogMagnitude.text)
                        minimumValue:0
                        maximumValue: 1500
                        stepSize: 1
                        tickmarksEnabled: true
                        anchors.left:parent.left
                        anchors.right:parent.right
                        anchors.rightMargin:20
                        anchors.leftMargin:20
                        implicitWidth: 150

                        style: SliderStyle {
                            handle: Rectangle {
                                id:slider
                                anchors.centerIn: parent
                                color: control.pressed ? "white" : "blue"
                                border.color: "blue"
                                border.width: 2
                                implicitWidth: 15
                                implicitHeight: 15
                                radius: 15
                            }
                            groove: Rectangle {
                                id: groovy
                                implicitHeight: 2
                                color: "black"
                                radius: 2
                            }
                        tickmarks: Repeater {
                            id: repeater
                            model: control.stepSize > 0 ? 1 + (control.maximumValue - control.minimumValue) / control.stepSize : 0

                            Rectangle {
                                color: "black"
                                width: noRec() ; height: noRec(); radius:noRec()
                                y:5
                                x: styleData.handleWidth / 2 + index * ((repeater.width - styleData.handleWidth) / (repeater.count-1))
                                function noRec(){
                                    if(index === 300 || index ===600 || index == 900 || index ===1200)return 6
                                    else return 0
                                }

                            }
                        }

                    }
                }
                }
                Rectangle{

                    function isVis(){
                        if (loadHelper.value>=125  && loadHelper.value<=200) return true
                        else if (loadHelper.value>=350  && loadHelper.value<=400) return true
                        else if (loadHelper.value>=550  && loadHelper.value<=600) return true
                        else if (loadHelper.value>=775  && loadHelper.value<=825) return true
                        else return false
                    }

                    color: UM.Theme.getColor("main_background")
                    border.width: UM.Theme.getSize("default_lining").width
                    border.color: UM.Theme.getColor("lining")
                    anchors.left:contentColumn.right
                    anchors.leftMargin: 10

                    height:contentColumn.height +14
                    width:  contentColumn.width

                    anchors.top:contentColumn.top
                    anchors.topMargin:-14
                    visible: isVis()

                    Label{
                    anchors.top:parent.top
                    anchors.topMargin: UM.Theme.getSize("default_margin").width
                    anchors.left:parent.left
                    anchors.leftMargin: UM.Theme.getSize("default_margin").width
                    font.bold:true

                    text: "Example:"

                    }



                    Image{
                    id: loadHelperImage
                        anchors.top: parent.top
                        anchors.topMargin: UM.Theme.getSize("default_margin").width*2
                        anchors.right:parent.right
                        anchors.rightMargin: UM.Theme.getSize("default_margin").width*4
                        anchors.left: parent.left
                        anchors.leftMargin: UM.Theme.getSize("default_margin").width*4
                        anchors.bottom:parent.bottom
                        anchors.bottomMargin: UM.Theme.getSize("default_margin").width*6



                        source:image()
                        function image(){
                            if (loadHelper.value>=150  && loadHelper.value<=250) return "Toddler.jpg"
                            else if (loadHelper.value>=350  && loadHelper.value<=450) return "Child.jpg"
                            else if (loadHelper.value>=550  && loadHelper.value<=650) return "Teenager.jpg"
                            else if (loadHelper.value>=750  && loadHelper.value<=850) return "Adult.jpg"
                            else return ""
                        }
                     }

                    Rectangle {
                        id: loadHelperSeparator
                        border.color:UM.Theme.getColor("lining")
                        color:UM.Theme.getColor("lining")
                        anchors.top: loadHelperImage.bottom
                        anchors.topMargin: UM.Theme.getSize("default_margin").width
                        anchors.right:parent.right
                        anchors.left:parent.left
                        width:parent.width
                        height:1

                    }

                    Text {
                        id: imageType
                        function getTextType(){
                            if (loadHelper.value>=150  && loadHelper.value<=250) return "<b>Toddler </b>"
                            else if (loadHelper.value>=350  && loadHelper.value<=450) return "<b>Young Child</b>"
                            else if (loadHelper.value>=550  && loadHelper.value<=650) return "<b>Teenager </b>"
                            else if (loadHelper.value>=750  && loadHelper.value<=850) return "<b>Adult </b>"
                            else return ""
                        }
                        anchors.top:loadHelperSeparator.bottom
                        anchors.topMargin: UM.Theme.getSize("default_margin").width
                        anchors.left: parent.left
                        anchors.leftMargin: UM.Theme.getSize("default_margin").width
                        text: getTextType()
                    }
                    Text{
                        function getTextType(){
                            if (loadHelper.value>=150  && loadHelper.value<=250) return "200 N (~45 lbs)"
                            else if (loadHelper.value>=350  && loadHelper.value<=450) return "400N (~90 lbs)"
                            else if (loadHelper.value>=550  && loadHelper.value<=650) return "600N (~130 lbs)"
                            else if (loadHelper.value>=750  && loadHelper.value<=850) return "800N (~180 lbs)"
                            else return ""
                        }
                        anchors.top:imageType.bottom
                        anchors.topMargin: UM.Theme.getSize("default_margin").width/2
                        anchors.left: parent.left
                        anchors.leftMargin: UM.Theme.getSize("default_margin").width
                        text: getTextType()
                    }

                }
            }
        }
    }
}

