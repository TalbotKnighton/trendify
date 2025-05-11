from pathlib import Path
from typing import List, Optional, ClassVar

from typeflow.serializable_model import SerializableModel, SerializableCollection
from typeflow.registry.base_registry import (
    BaseComponent,
    ByTypeComponent,
    registries,
    OBJECT_REGISTRY,
)


# Define example models
class Person(SerializableModel):
    """A person model using SerializableModel (without registry integration)"""

    model_version: ClassVar[str] = "1.0.0"

    full_name: str
    age: int
    email: Optional[str] = None


class Address(BaseComponent):
    """An address model using BaseComponent (with registry capability)"""

    model_version: ClassVar[str] = "1.1.0"

    street: str
    city: str
    postal_code: str
    country: str = "USA"


class Contact(ByTypeComponent):
    """A contact model using ByTypeComponent (auto-registers in global registry)"""

    model_version: ClassVar[str] = "1.0.0"

    person: Person
    addresses: List[Address] = []
    primary_address_index: Optional[int] = None

    @property
    def primary_address(self) -> Optional[Address]:
        """Get the primary address if set"""
        if (
            self.primary_address_index is not None
            and 0 <= self.primary_address_index < len(self.addresses)
        ):
            return self.addresses[self.primary_address_index]
        return None


def example_usage():
    # Create instances
    person = Person(
        name="example_person", full_name="John Doe", age=30, email="john@example.com"
    )

    # Create and register an address
    home_address = Address(
        name="home", street="123 Main St", city="Anytown", postal_code="12345"
    )
    registry = registries.get_registry(OBJECT_REGISTRY)
    home_address.register(registry)

    # Create another address
    work_address = Address(
        name="work",
        street="456 Office Blvd",
        city="Workville",
        postal_code="67890",
        country="Canada",
    )
    work_address.register(registry)

    # Create a contact - it auto-registers in the registry
    contact = Contact(
        name="john_contact",
        person=person,
        addresses=[home_address, work_address],
        primary_address_index=0,
    )

    # Serialize to JSON
    json_data = contact.model_dump_json(indent=2)
    print(f"Serialized data:\n{json_data}\n")

    # Save to file
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)
    contact.save_to_file(output_dir / "contact.json")

    # Deserialize from JSON using the base class
    # It will automatically determine the correct type
    loaded_contact = SerializableModel.from_json(json_data)

    print(f"Loaded contact type: {type(loaded_contact).__name__}")
    print(
        f"Person: {loaded_contact.person.full_name}, Age: {loaded_contact.person.age}"
    )
    print(
        f"Primary address: {loaded_contact.primary_address.street}, {loaded_contact.primary_address.city}"
    )

    # Create a collection
    collection = SerializableCollection(name="contacts")
    collection.append(contact)

    # Create another contact and add it to collection
    another_person = Person(name="example_person_2", full_name="Jane Smith", age=28)
    another_contact = Contact(name="jane_contact", person=another_person)
    collection.append(another_contact)

    # Save collection
    collection.save_to_file(output_dir / "contact_collection.json")

    # Load collection
    loaded_collection = SerializableModel.from_file(
        output_dir / "contact_collection.json"
    )
    print(f"\nLoaded collection with {len(loaded_collection)} items")

    # Get a component from registry
    retrieved_contact = registry.get_object(Contact, "john_contact")
    print(f"Retrieved from registry: {retrieved_contact.person.full_name}")

    # Check version information
    print(f"\nAddress version: {home_address.type_info.version}")
    print(f"Contact version: {contact.type_info.version}")


if __name__ == "__main__":
    example_usage()
