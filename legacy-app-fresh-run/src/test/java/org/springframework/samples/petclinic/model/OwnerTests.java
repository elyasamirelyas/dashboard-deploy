package org.springframework.samples.petclinic.model;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;

import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

class OwnerTests {

    private Owner owner;

    @BeforeEach
    void setUp() {
        owner = new Owner();
        owner.setFirstName("John");
        owner.setLastName("Doe");
        owner.setAddress("123 Main St");
        owner.setCity("Springfield");
        owner.setTelephone("1234567890");
    }

    @Test
    void testGetAndSetAddress() {
        String address = "456 Oak Avenue";
        owner.setAddress(address);
        assertEquals(address, owner.getAddress());
    }

    @Test
    void testGetAndSetCity() {
        String city = "Boston";
        owner.setCity(city);
        assertEquals(city, owner.getCity());
    }

    @Test
    void testGetAndSetTelephone() {
        String telephone = "9876543210";
        owner.setTelephone(telephone);
        assertEquals(telephone, owner.getTelephone());
    }

    @Test
    void testGetPetsInternal_InitializesEmptySet() {
        Set<Pet> pets = owner.getPetsInternal();
        assertNotNull(pets);
        assertTrue(pets.isEmpty());
    }

    @Test
    void testAddPet_Success() {
        Pet pet = new Pet();
        pet.setName("Fluffy");
        
        owner.addPet(pet);
        
        Set<Pet> pets = owner.getPetsInternal();
        assertEquals(1, pets.size());
        assertTrue(pets.contains(pet));
        assertEquals(owner, pet.getOwner());
    }

    @Test
    void testGetPets_ReturnsSortedUnmodifiableList() {
        Pet pet1 = new Pet();
        pet1.setName("Zebra");
        Pet pet2 = new Pet();
        pet2.setName("Alpha");
        Pet pet3 = new Pet();
        pet3.setName("Beta");
        
        owner.addPet(pet1);
        owner.addPet(pet2);
        owner.addPet(pet3);
        
        List<Pet> pets = owner.getPets();
        
        assertEquals(3, pets.size());
        assertEquals("Alpha", pets.get(0).getName());
        assertEquals("Beta", pets.get(1).getName());
        assertEquals("Zebra", pets.get(2).getName());
        
        assertThrows(UnsupportedOperationException.class, () -> {
            pets.add(new Pet());
        });
    }

    @Test
    void testSetPets_FromList() {
        Pet pet1 = new Pet();
        pet1.setName("Max");
        Pet pet2 = new Pet();
        pet2.setName("Bella");
        
        List<Pet> petList = List.of(pet1, pet2);
        owner.setPets(petList);
        
        Set<Pet> petsInternal = owner.getPetsInternal();
        assertEquals(2, petsInternal.size());
    }

    @Test
    void testGetPet_ByName_Success() {
        Pet pet = new Pet();
        pet.setName("Buddy");
        owner.addPet(pet);
        
        Pet found = owner.getPet("Buddy");
        
        assertNotNull(found);
        assertEquals("Buddy", found.getName());
    }

    @Test
    void testGetPet_ByName_CaseInsensitive() {
        Pet pet = new Pet();
        pet.setName("Buddy");
        owner.addPet(pet);
        
        Pet found = owner.getPet("BUDDY");
        
        assertNotNull(found);
        assertEquals("Buddy", found.getName());
    }

    @Test
    void testGetPet_ByName_NotFound() {
        Pet pet = new Pet();
        pet.setName("Buddy");
        owner.addPet(pet);
        
        Pet found = owner.getPet("Nonexistent");
        
        assertNull(found);
    }

    @Test
    void testGetPet_WithIgnoreNew_False() {
        Pet pet = new Pet();
        pet.setName("NewPet");
        owner.addPet(pet);
        
        Pet found = owner.getPet("NewPet", false);
        
        assertNotNull(found);
    }

    @Test
    void testGetPet_WithIgnoreNew_True_NewPet() {
        Pet pet = new Pet();
        pet.setName("NewPet");
        owner.addPet(pet);
        
        Pet found = owner.getPet("NewPet", true);
        
        assertNull(found);
    }

    @Test
    void testGetPet_WithIgnoreNew_True_ExistingPet() {
        Pet pet = new Pet();
        pet.setId(1);
        pet.setName("ExistingPet");
        owner.addPet(pet);
        
        Pet found = owner.getPet("ExistingPet", true);
        
        assertNotNull(found);
        assertEquals("ExistingPet", found.getName());
    }

    @Test
    void testGetPet_EmptyPets_ReturnsNull() {
        Pet found = owner.getPet("AnyName");
        assertNull(found);
    }

    @Test
    void testToString_ContainsExpectedFields() {
        owner.setId(1);
        String result = owner.toString();
        
        assertNotNull(result);
        assertTrue(result.contains("id"));
        assertTrue(result.contains("lastName"));
        assertTrue(result.contains("firstName"));
        assertTrue(result.contains("address"));
        assertTrue(result.contains("city"));
        assertTrue(result.contains("telephone"));
    }

    @Test
    void testMultiplePets_DifferentNames() {
        Pet pet1 = new Pet();
        pet1.setName("Dog");
        Pet pet2 = new Pet();
        pet2.setName("Cat");
        
        owner.addPet(pet1);
        owner.addPet(pet2);
        
        assertEquals(2, owner.getPetsInternal().size());
        assertNotNull(owner.getPet("Dog"));
        assertNotNull(owner.getPet("Cat"));
    }
}