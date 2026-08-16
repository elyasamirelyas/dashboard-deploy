package org.springframework.samples.petclinic.model;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;

import org.junit.jupiter.api.Test;

/**
 * Plain JUnit 5 unit tests for {@link Owner}.
 *
 * Owner is a real automated-pipeline candidate (lowest non-excluded line
 * coverage in the baseline JaCoCo report, ~59.5%) but had no dedicated unit
 * test class of its own before this one - it was only exercised indirectly
 * through the REST controller tests. These tests target the getter/setter
 * pairs, the pet collection management (addPet / getPets), and the
 * case-insensitive / "ignoreNew" lookup behaviour of getPet(), which was
 * previously untested.
 *
 * No Mockito, no Spring context - Owner and Pet are plain JavaBeans so a
 * pure unit test is sufficient and faster/more reliable than a
 * @SpringBootTest.
 */
class OwnerTests {

    @Test
    void shouldSetAndGetAddressCityTelephone() {
        Owner owner = new Owner();
        owner.setAddress("110 W. Liberty St.");
        owner.setCity("Madison");
        owner.setTelephone("6085551023");

        assertThat(owner.getAddress()).isEqualTo("110 W. Liberty St.");
        assertThat(owner.getCity()).isEqualTo("Madison");
        assertThat(owner.getTelephone()).isEqualTo("6085551023");
    }

    @Test
    void newOwnerShouldHaveNoPets() {
        Owner owner = new Owner();

        assertThat(owner.getPets()).isEmpty();
    }

    @Test
    void addPetShouldStoreItAndSetBackReferenceToOwner() {
        Owner owner = new Owner();
        Pet pet = new Pet();
        pet.setName("Leo");

        owner.addPet(pet);

        assertThat(owner.getPets()).hasSize(1);
        assertThat(owner.getPets()).contains(pet);
        // addPet must set the owner back-reference on the pet itself
        assertThat(pet.getOwner()).isSameAs(owner);
    }

    @Test
    void getPetsShouldReturnPetsSortedByName() {
        Owner owner = new Owner();
        Pet zeus = new Pet();
        zeus.setName("Zeus");
        Pet amy = new Pet();
        amy.setName("Amy");
        Pet leo = new Pet();
        leo.setName("Leo");

        owner.addPet(zeus);
        owner.addPet(amy);
        owner.addPet(leo);

        List<Pet> pets = owner.getPets();
        assertThat(pets).extracting(Pet::getName)
            .containsExactly("Amy", "Leo", "Zeus");
    }

    @Test
    void getPetsShouldBeUnmodifiable() {
        Owner owner = new Owner();
        Pet pet = new Pet();
        pet.setName("Leo");
        owner.addPet(pet);

        List<Pet> pets = owner.getPets();

        assertThatUnsupportedOperation(() -> pets.add(new Pet()));
    }

    private void assertThatUnsupportedOperation(Runnable action) {
        try {
            action.run();
            org.junit.jupiter.api.Assertions.fail("Expected UnsupportedOperationException");
        } catch (UnsupportedOperationException expected) {
            // expected - getPets() is documented as returning an unmodifiable list
        }
    }

    @Test
    void getPetByNameShouldBeCaseInsensitive() {
        Owner owner = new Owner();
        Pet pet = new Pet();
        pet.setName("Leo");
        owner.addPet(pet);

        assertThat(owner.getPet("leo")).isSameAs(pet);
        assertThat(owner.getPet("LEO")).isSameAs(pet);
        assertThat(owner.getPet("LeO")).isSameAs(pet);
    }

    @Test
    void getPetByNameShouldReturnNullWhenNoMatch() {
        Owner owner = new Owner();
        Pet pet = new Pet();
        pet.setName("Leo");
        owner.addPet(pet);

        assertThat(owner.getPet("Basil")).isNull();
    }

    @Test
    void getPetByNameWithIgnoreNewTrueShouldSkipUnsavedPets() {
        Owner owner = new Owner();
        Pet newPet = new Pet();
        newPet.setName("Leo");
        // a Pet with no id is considered "new" (BaseEntity#isNew: id == null)
        owner.addPet(newPet);

        // ignoreNew = true: a pet that hasn't been saved yet (id == null) must not match
        assertThat(owner.getPet("Leo", true)).isNull();

        // once it has an id it's no longer "new" and should be found
        newPet.setId(1);
        assertThat(owner.getPet("Leo", true)).isSameAs(newPet);
    }

    @Test
    void getPetByNameWithIgnoreNewFalseShouldIncludeUnsavedPets() {
        Owner owner = new Owner();
        Pet newPet = new Pet();
        newPet.setName("Leo");
        owner.addPet(newPet);

        // ignoreNew = false: unsaved pets are still matched
        assertThat(owner.getPet("Leo", false)).isSameAs(newPet);
    }

    @Test
    void toStringShouldContainKeyOwnerFields() {
        Owner owner = new Owner();
        owner.setFirstName("George");
        owner.setLastName("Franklin");
        owner.setAddress("110 W. Liberty St.");
        owner.setCity("Madison");
        owner.setTelephone("6085551023");

        String result = owner.toString();

        assertThat(result).contains("George");
        assertThat(result).contains("Franklin");
        assertThat(result).contains("Madison");
        assertThat(result).contains("6085551023");
    }
}