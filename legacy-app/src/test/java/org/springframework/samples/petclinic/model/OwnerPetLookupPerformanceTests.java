package org.springframework.samples.petclinic.model;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

/**
 * Lightweight performance sanity check for Owner.getPets() (sorts the whole
 * pet collection on every call) and Owner.getPet(name) (a linear scan over
 * the pet collection on every call). Both are realistic hot paths - the
 * REST layer calls getPets() every time it serializes an OwnerDto.
 *
 * This is deliberately NOT a JMH microbenchmark: JMH is a new Maven
 * dependency, and this environment has no verified access to Maven Central
 * to confirm it resolves, so introducing it here would be an unverified
 * claim. This is a plain JUnit timing sanity check instead - it asserts a
 * generous upper bound (to stay stable across slower CI machines) and
 * prints the actual measured time so it's useful as real evaluation
 * evidence, not just a pass/fail gate.
 */
class OwnerPetLookupPerformanceTests {

    private static final int PET_COUNT = 5_000;
    private static final int LOOKUP_ITERATIONS = 5_000;

    @Test
    void getPetsShouldSortLargeCollectionsWithinAReasonableTime() {
        Owner owner = buildOwnerWithPets(PET_COUNT);

        long start = System.nanoTime();
        int size = owner.getPets().size();
        long elapsedMs = (System.nanoTime() - start) / 1_000_000;

        System.out.println("[perf] getPets() over " + PET_COUNT
            + " pets took " + elapsedMs + " ms");

        assertThat(size).isEqualTo(PET_COUNT);
        assertThat(elapsedMs).isLessThan(2_000L); // generous upper bound
    }

    @Test
    void getPetByNameShouldRepeatedlyScanLargeCollectionsWithinAReasonableTime() {
        Owner owner = buildOwnerWithPets(PET_COUNT);
        String targetName = "pet-" + (PET_COUNT - 1); // worst case: last match

        long start = System.nanoTime();
        for (int i = 0; i < LOOKUP_ITERATIONS; i++) {
            owner.getPet(targetName);
        }
        long elapsedMs = (System.nanoTime() - start) / 1_000_000;

        System.out.println("[perf] " + LOOKUP_ITERATIONS
            + " x getPet(name) over " + PET_COUNT + " pets took " + elapsedMs + " ms");

        assertThat(owner.getPet(targetName)).isNotNull();
        assertThat(elapsedMs).isLessThan(5_000L); // generous upper bound
    }

    private Owner buildOwnerWithPets(int count) {
        Owner owner = new Owner();
        for (int i = 0; i < count; i++) {
            Pet pet = new Pet();
            pet.setName("pet-" + i);
            owner.addPet(pet);
        }
        return owner;
    }
}