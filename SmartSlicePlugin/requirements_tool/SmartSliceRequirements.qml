import QtQuick 2.4
import QtQuick.Controls 1.2
import QtQuick.Layouts 1.1
import QtQuick.Controls.Styles 1.1

import UM 1.2 as UM
import Cura 1.0 as Cura

import SmartSlice 1.0 as SmartSlice

Item {
    width: childrenRect.width
    height: childrenRect.height
    UM.I18nCatalog { id: catalog; name: "smartslice"}

    property string targetSafetyFactorText

    Grid {
        id: textfields;

        anchors.top: parent.top;

        columns: 2;
        flow: Grid.TopToBottom;
        spacing: Math.round(UM.Theme.getSize("default_margin").width / 2);

        Label {
            height: UM.Theme.getSize("setting_control").height;

            font: UM.Theme.getFont("default");
            renderType: Text.NativeRendering

            text: catalog.i18nc("@action:button", "Factor of Safety \u2265")
        }

        Label {
            height: UM.Theme.getSize("setting_control").height;

            font: UM.Theme.getFont("default");
            renderType: Text.NativeRendering

            text: catalog.i18nc("@action:button", "Max Deflection  \u2264")
        }

        TextField {
            id: valueSafetyFactor
            width: UM.Theme.getSize("setting_control").width;
            height: UM.Theme.getSize("setting_control").height;
            style: UM.Theme.styles.text_field;

            onEditingFinished: {
                UM.ActiveTool.setProperty("TargetSafetyFactor", text)
            }

            /*onTextChanged: {
            }*/

            placeholderText: catalog.i18nc("@action:button", "Must be above 1")
            property string unit: "[1]";
        }

        TextField {
            id: valueMaxDeflect
            width: UM.Theme.getSize("setting_control").width;
            height: UM.Theme.getSize("setting_control").height;
            style: UM.Theme.styles.text_field;

            onEditingFinished: {
                UM.ActiveTool.setProperty("MaxDisplacement", text)
            }

            /*onTextChanged: {
            }*/

            //text: SmartSlice.Cloud.targetMaximalDisplacement
            placeholderText: ""
            property string unit: "[mm]";
        }

        Binding {
            target: valueSafetyFactor
            property: "text"
            value: UM.ActiveTool.properties.getValue("TargetSafetyFactor")
        }

        Binding {
            target: valueMaxDeflect
            property: "text"
            value: UM.ActiveTool.properties.getValue("MaxDisplacement")
        }

    }
}
