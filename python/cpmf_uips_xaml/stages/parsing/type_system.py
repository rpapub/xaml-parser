"""Type system modeling for .NET types with generic parameters.

This module provides utilities to parse and analyze .NET type signatures from
XAML type annotations, enabling type flow analysis through transformations.
"""

import re
from dataclasses import dataclass
from typing import Self


@dataclass
class TypeInfo:
    """Represents a .NET type with full fidelity.

    This class models .NET types including generic types, arrays, and provides
    utilities for type inference through common operations (method calls,
    dictionary access, etc.).

    Attributes:
        full_name: Full type name (e.g., "System.String")
        namespace: Namespace portion (e.g., "System")
        name: Type name only (e.g., "String")
        generic_args: Generic type arguments for generic types
        is_array: Whether this is an array type
        array_rank: Dimensionality for arrays (1 for T[], 2 for T[,], etc.)
    """

    full_name: str
    namespace: str
    name: str
    generic_args: list[Self] | None = None
    is_array: bool = False
    array_rank: int = 0

    @staticmethod
    def parse(type_str: str) -> "TypeInfo":
        """Parse .NET type string to TypeInfo.

        Handles various .NET type formats:
        - Simple: "System.String"
        - Generic: "Dictionary`2[System.String,System.Object]"
        - Short generic: "Dictionary`2[String,Object]"
        - Arrays: "String[]", "Int32[,]"
        - Nested generics: "List`1[Dictionary`2[String,Object]]"

        Args:
            type_str: .NET type signature string

        Returns:
            TypeInfo object with parsed components

        Examples:
            >>> TypeInfo.parse("System.String")
            TypeInfo(full_name="System.String", namespace="System", name="String")

            >>> TypeInfo.parse("Dictionary`2[String,Object]")
            TypeInfo(name="Dictionary", generic_args=[TypeInfo("String"), TypeInfo("Object")])

            >>> TypeInfo.parse("String[]")
            TypeInfo(name="String", is_array=True, array_rank=1)
        """
        type_str = type_str.strip()

        # Handle array types: T[], T[,], etc.
        array_match = re.match(r"^(.+?)(\[\s*,*\s*\])$", type_str)
        if array_match:
            base_type_str = array_match.group(1)
            array_brackets = array_match.group(2)
            array_rank = array_brackets.count(",") + 1

            base_type = TypeInfo.parse(base_type_str)
            base_type.is_array = True
            base_type.array_rank = array_rank
            return base_type

        # Handle generic types: Name`N[T1,T2,...]
        generic_match = re.match(r"^([^`\[]+)(`\d+)?\[(.+)\]$", type_str)
        if generic_match:
            type_name = generic_match.group(1).strip()
            generic_args_str = generic_match.group(3)

            # Parse generic arguments
            generic_args = TypeInfo._parse_generic_args(generic_args_str)

            # Split namespace and name
            if "." in type_name:
                parts = type_name.rsplit(".", 1)
                namespace = parts[0]
                name = parts[1]
            else:
                namespace = ""
                name = type_name

            return TypeInfo(
                full_name=type_str,
                namespace=namespace,
                name=name,
                generic_args=generic_args,
                is_array=False,
                array_rank=0,
            )

        # Simple type: System.String or String
        if "." in type_str:
            parts = type_str.rsplit(".", 1)
            namespace = parts[0]
            name = parts[1]
        else:
            namespace = ""
            name = type_str

        return TypeInfo(
            full_name=type_str,
            namespace=namespace,
            name=name,
            generic_args=None,
            is_array=False,
            array_rank=0,
        )

    @staticmethod
    def _parse_generic_args(args_str: str) -> list["TypeInfo"]:
        """Parse comma-separated generic arguments, respecting nested brackets.

        Args:
            args_str: String like "String,Object" or "String,Dictionary`2[String,Object]"

        Returns:
            List of parsed TypeInfo objects
        """
        args = []
        current_arg = ""
        bracket_depth = 0

        for char in args_str:
            if char == "[":
                bracket_depth += 1
                current_arg += char
            elif char == "]":
                bracket_depth -= 1
                current_arg += char
            elif char == "," and bracket_depth == 0:
                # Top-level comma - argument separator
                if current_arg.strip():
                    args.append(TypeInfo.parse(current_arg.strip()))
                current_arg = ""
            else:
                current_arg += char

        # Don't forget last argument
        if current_arg.strip():
            args.append(TypeInfo.parse(current_arg.strip()))

        return args

    def get_element_type(self) -> "TypeInfo | None":
        """Get element type for collections/arrays.

        For arrays, returns the element type (T[] → T).
        For dictionaries, returns the value type (Dict<K,V> → V).
        For lists/enumerables, returns the element type (List<T> → T).

        Returns:
            TypeInfo for element/value type, or None if not applicable

        Examples:
            >>> t = TypeInfo.parse("String[]")
            >>> t.get_element_type()
            TypeInfo(name="String")

            >>> t = TypeInfo.parse("Dictionary`2[String,Object]")
            >>> t.get_element_type()
            TypeInfo(name="Object")

            >>> t = TypeInfo.parse("List`1[Int32]")
            >>> t.get_element_type()
            TypeInfo(name="Int32")
        """
        # Arrays: T[] → T
        if self.is_array:
            return TypeInfo(
                full_name=self.full_name.split("[")[0],
                namespace=self.namespace,
                name=self.name,
                generic_args=None,
                is_array=False,
                array_rank=0,
            )

        # Generic collections
        if self.generic_args:
            # Dictionary: return value type (second generic arg)
            if self.name == "Dictionary" and len(self.generic_args) >= 2:
                return self.generic_args[1]

            # List, IEnumerable, ICollection, etc.: return element type (first arg)
            if self.name in [
                "List",
                "IEnumerable",
                "ICollection",
                "IList",
                "HashSet",
                "Queue",
                "Stack",
            ]:
                return self.generic_args[0]

        return None

    def infer_method_return_type(self, method_name: str) -> "TypeInfo | None":
        """Infer return type of method call on this type.

        Uses knowledge of common .NET method signatures to infer return types.
        This is not exhaustive but covers common UiPath operations.

        Args:
            method_name: Method name (e.g., "ToString", "ToUpper")

        Returns:
            TypeInfo for return type, or None if unknown

        Examples:
            >>> t = TypeInfo.parse("System.Object")
            >>> t.infer_method_return_type("ToString")
            TypeInfo(name="String")

            >>> t = TypeInfo.parse("System.String")
            >>> t.infer_method_return_type("ToUpper")
            TypeInfo(name="String")
        """
        # Universal methods (on Object)
        if method_name == "ToString":
            return TypeInfo(full_name="System.String", namespace="System", name="String")
        if method_name == "GetType":
            return TypeInfo(full_name="System.Type", namespace="System", name="Type")

        # String methods
        if self.name == "String" or self.namespace == "System" and self.name == "String":
            string_methods = {
                "ToUpper": "String",
                "ToLower": "String",
                "Trim": "String",
                "TrimStart": "String",
                "TrimEnd": "String",
                "Substring": "String",
                "Replace": "String",
                "Split": "String[]",
                "Contains": "Boolean",
                "StartsWith": "Boolean",
                "EndsWith": "Boolean",
                "IndexOf": "Int32",
                "Length": "Int32",
            }
            if method_name in string_methods:
                return TypeInfo.parse(f"System.{string_methods[method_name]}")

        # Collection methods
        if self.generic_args:
            if method_name == "Count":
                return TypeInfo(full_name="System.Int32", namespace="System", name="Int32")
            if method_name == "ContainsKey" or method_name == "Contains":
                return TypeInfo(full_name="System.Boolean", namespace="System", name="Boolean")
            if method_name == "First" or method_name == "FirstOrDefault":
                return self.get_element_type()
            if method_name == "Last" or method_name == "LastOrDefault":
                return self.get_element_type()

        # Array methods
        if self.is_array:
            if method_name == "Length":
                return TypeInfo(full_name="System.Int32", namespace="System", name="Int32")
            if method_name == "First" or method_name == "FirstOrDefault":
                return self.get_element_type()

        # DateTime methods
        if self.name == "DateTime":
            datetime_methods = {
                "AddDays": "DateTime",
                "AddHours": "DateTime",
                "AddMinutes": "DateTime",
                "AddSeconds": "DateTime",
                "Date": "DateTime",
                "Day": "Int32",
                "Month": "Int32",
                "Year": "Int32",
                "Hour": "Int32",
                "Minute": "Int32",
                "Second": "Int32",
            }
            if method_name in datetime_methods:
                return TypeInfo.parse(f"System.{datetime_methods[method_name]}")

        return None

    def infer_property_type(self, property_name: str) -> "TypeInfo | None":
        """Infer type of property access on this type.

        Args:
            property_name: Property name (e.g., "Length", "Count")

        Returns:
            TypeInfo for property type, or None if unknown
        """
        # String properties
        if self.name == "String":
            if property_name == "Length":
                return TypeInfo(full_name="System.Int32", namespace="System", name="Int32")

        # Collection properties
        if self.generic_args or self.is_array:
            if property_name == "Count" or property_name == "Length":
                return TypeInfo(full_name="System.Int32", namespace="System", name="Int32")

        # DateTime properties
        if self.name == "DateTime":
            datetime_props = {
                "Date": "DateTime",
                "Day": "Int32",
                "Month": "Int32",
                "Year": "Int32",
                "Hour": "Int32",
                "Minute": "Int32",
                "Second": "Int32",
                "Millisecond": "Int32",
                "DayOfWeek": "DayOfWeek",
                "DayOfYear": "Int32",
            }
            if property_name in datetime_props:
                return TypeInfo.parse(f"System.{datetime_props[property_name]}")

        return None

    def __str__(self) -> str:
        """String representation showing full type signature."""
        if self.is_array:
            brackets = "[" + "," * (self.array_rank - 1) + "]"
            return f"{self.name}{brackets}"
        if self.generic_args:
            args_str = ", ".join(str(arg) for arg in self.generic_args)
            return f"{self.name}<{args_str}>"
        return self.name

    def __repr__(self) -> str:
        """Debug representation."""
        return f"TypeInfo({self.full_name})"
