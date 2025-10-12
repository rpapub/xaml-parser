"""Pytest configuration for unit tests.

Unit tests should be:
- Fast (<10ms per test)
- Isolated (no file I/O, no network)
- Focused on single functions/classes
- Use inline XAML strings or mocks
"""

import pytest


@pytest.fixture
def simple_xaml():
    """Minimal valid XAML for testing."""
    return """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main"
          xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence DisplayName="Simple Sequence">
    <LogMessage DisplayName="Log" Text="Hello" />
  </Sequence>
</Activity>"""


@pytest.fixture
def xaml_with_argument():
    """XAML with a single argument for testing."""
    return """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main"
          xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
          xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation">
  <x:Members>
    <x:Property Name="in_TestArg" Type="InArgument(x:String)"
                sap2010:Annotation.AnnotationText="Test argument" />
  </x:Members>
  <Sequence DisplayName="Test Sequence">
    <LogMessage Text="[in_TestArg]" />
  </Sequence>
</Activity>"""


@pytest.fixture
def xaml_with_variable():
    """XAML with a variable for testing."""
    return """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main"
          xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence DisplayName="Sequence with Variable">
    <Sequence.Variables>
      <Variable x:TypeArguments="x:String" Name="testVar" Default="default value" />
    </Sequence.Variables>
    <Assign DisplayName="Assign testVar">
      <Assign.To>
        <OutArgument x:TypeArguments="x:String">[testVar]</OutArgument>
      </Assign.To>
      <Assign.Value>
        <InArgument x:TypeArguments="x:String">New Value</InArgument>
      </Assign.Value>
    </Assign>
  </Sequence>
</Activity>"""


@pytest.fixture
def xaml_with_activities():
    """XAML with multiple activities for testing."""
    return """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main"
          xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence DisplayName="Multiple Activities">
    <LogMessage DisplayName="Log 1" Text="First" Level="Info" />
    <LogMessage DisplayName="Log 2" Text="Second" Level="Warn" />
    <If DisplayName="Conditional" Condition="[True]">
      <If.Then>
        <LogMessage Text="Then branch" />
      </If.Then>
      <If.Else>
        <LogMessage Text="Else branch" />
      </If.Else>
    </If>
  </Sequence>
</Activity>"""


@pytest.fixture
def malformed_xaml():
    """Invalid XAML for error testing."""
    return """<?xml version="1.0"?>
<Activity>
  <Sequence>
    <Unclosed Tag
  </Sequence>
</Activity>"""


@pytest.fixture
def empty_xaml():
    """Empty/minimal XAML for edge case testing."""
    return """<?xml version="1.0" encoding="utf-8"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" />"""


@pytest.fixture
def xaml_with_multiple_arguments():
    """XAML with multiple arguments (in/out/inout) for testing."""
    return """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main"
          xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
          xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation">
  <x:Members>
    <x:Property Name="in_FilePath" Type="InArgument(x:String)"
                sap2010:Annotation.AnnotationText="Input file path" default="config.json" />
    <x:Property Name="out_Result" Type="OutArgument(x:Int32)"
                sap2010:Annotation.AnnotationText="Processing result" />
    <x:Property Name="io_Data" Type="InOutArgument(x:String)" />
  </x:Members>
  <Sequence DisplayName="Main Sequence">
    <LogMessage Text="[in_FilePath]" />
  </Sequence>
</Activity>"""


@pytest.fixture
def xaml_with_nested_variables():
    """XAML with variables at different scopes for testing."""
    return """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main"
          xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence DisplayName="Outer Sequence">
    <Sequence.Variables>
      <Variable x:TypeArguments="x:String" Name="outerVar" Default="outer" />
    </Sequence.Variables>
    <Sequence DisplayName="Inner Sequence">
      <Sequence.Variables>
        <Variable x:TypeArguments="x:Int32" Name="innerVar" Default="42" />
      </Sequence.Variables>
      <LogMessage Text="[outerVar + innerVar.ToString()]" />
    </Sequence>
  </Sequence>
</Activity>"""


@pytest.fixture
def xaml_with_nested_activities():
    """XAML with nested activity hierarchy for testing."""
    return """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main"
          xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
          xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation">
  <Sequence DisplayName="Root Sequence" sap2010:Annotation.AnnotationText="Root annotation">
    <If DisplayName="Check Condition" Condition="[True]">
      <If.Then>
        <Sequence DisplayName="Then Branch">
          <LogMessage DisplayName="Then Log" Text="Then executed" Level="Info" />
          <Assign DisplayName="Assign Value" Value="[123]" />
        </Sequence>
      </If.Then>
      <If.Else>
        <LogMessage DisplayName="Else Log" Text="Else executed" Level="Warn" />
      </If.Else>
    </If>
  </Sequence>
</Activity>"""


@pytest.fixture
def xaml_with_expressions():
    """XAML with various expression types for testing."""
    return """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main"
          xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence DisplayName="Expression Test">
    <If Condition="[myVar > 10 AndAlso status.ToLower() = &quot;ready&quot;]">
      <If.Then>
        <Assign DisplayName="Assign Result"
                Value="[String.Format(&quot;Count: {0}&quot;, counter)]">
          <Assign.To>
            <OutArgument x:TypeArguments="x:String">[result]</OutArgument>
          </Assign.To>
        </Assign>
      </If.Then>
    </If>
    <LogMessage Text="[New Exception(&quot;Error: &quot; + message)]" Level="Error" />
  </Sequence>
</Activity>"""


@pytest.fixture
def xaml_with_annotations():
    """XAML with annotations including HTML entities for testing."""
    return """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main"
          xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
          xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation">
  <Sequence DisplayName="Root"
            sap2010:Annotation.AnnotationText=
              "Root annotation with &lt;HTML&gt; &amp; entities&#39;">
    <LogMessage DisplayName="Log 1" Text="Test"
                sap2010:Annotation.AnnotationText="First log: use &quot;quotes&quot;" />
    <LogMessage DisplayName="Log 2" Text="Test2"
                sap2010:Annotation.AnnotationText="Second log" />
  </Sequence>
</Activity>"""


@pytest.fixture
def xaml_with_namespaces():
    """XAML with multiple namespaces for testing."""
    return """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main"
          xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
          xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
          xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
          xmlns:ui="http://schemas.uipath.com/workflow/activities"
          xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib"
          ExpressionActivityEditor="VisualBasic">
  <TextExpression.NamespacesForImplementation>
    <scg:List x:TypeArguments="x:String" Capacity="4">
      <x:String>System</x:String>
      <x:String>System.Collections.Generic</x:String>
    </scg:List>
  </TextExpression.NamespacesForImplementation>
  <TextExpression.ReferencesForImplementation>
    <scg:List x:TypeArguments="AssemblyReference" Capacity="2">
      <AssemblyReference>UiPath.System.Activities, Version=23.10.0,
                         Culture=neutral</AssemblyReference>
      <AssemblyReference>UiPath.UIAutomation.Activities</AssemblyReference>
    </scg:List>
  </TextExpression.ReferencesForImplementation>
  <Sequence DisplayName="Main">
    <LogMessage Text="Test" />
  </Sequence>
</Activity>"""
