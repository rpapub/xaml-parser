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
