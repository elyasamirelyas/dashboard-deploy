package com.spring.crud.demo.utils;

import com.spring.crud.demo.model.SportsIcon;
import com.spring.crud.demo.model.Student;
import com.spring.crud.demo.model.emp.Employee;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class UtilityHelperTests {

    @Test
    void testStudentSupplier_shouldReturnListOfStudents() {
        List<Student> students = UtilityHelper.studentSupplier.get();

        assertNotNull(students);
        assertEquals(12, students.size());
        
        Student firstStudent = students.get(0);
        assertEquals(1, firstStudent.getRollNo());
        assertEquals("Santhosh", firstStudent.getFirstName());
        assertEquals("Vernekar", firstStudent.getLastName());
        assertEquals(300.0f, firstStudent.getMarks());
    }

    @Test
    void testStudentSupplier_shouldContainExpectedStudents() {
        List<Student> students = UtilityHelper.studentSupplier.get();

        assertTrue(students.stream().anyMatch(s -> "Ram".equals(s.getFirstName())));
        assertTrue(students.stream().anyMatch(s -> "Yash".equals(s.getFirstName())));
        assertTrue(students.stream().anyMatch(s -> 950.0f == s.getMarks()));
    }

    @Test
    void testStudentSupplier_shouldReturnNewListEachTime() {
        List<Student> students1 = UtilityHelper.studentSupplier.get();
        List<Student> students2 = UtilityHelper.studentSupplier.get();

        assertNotNull(students1);
        assertNotNull(students2);
        assertNotSame(students1, students2);
        assertEquals(students1.size(), students2.size());
    }

    @Test
    void testSportIconsSupplier_shouldReturnListOfSportsIcons() {
        List<SportsIcon> sportsIcons = UtilityHelper.sportIconsSupplier.get();

        assertNotNull(sportsIcons);
        assertEquals(7, sportsIcons.size());
        
        SportsIcon firstIcon = sportsIcons.get(0);
        assertEquals("Virat", firstIcon.getName());
        assertEquals("King Kohli", firstIcon.getSpecialName());
        assertEquals("Cricketer", firstIcon.getSports());
        assertEquals(33, firstIcon.getAge());
        assertFalse(firstIcon.isOlampian());
    }

    @Test
    void testSportIconsSupplier_shouldContainOlympians() {
        List<SportsIcon> sportsIcons = UtilityHelper.sportIconsSupplier.get();

        long olympianCount = sportsIcons.stream()
                .filter(SportsIcon::isOlampian)
                .count();

        assertEquals(4, olympianCount);
        assertTrue(sportsIcons.stream().anyMatch(s -> "Neeraj".equals(s.getName()) && s.isOlampian()));
    }

    @Test
    void testSportIconsSupplier_shouldContainNonOlympians() {
        List<SportsIcon> sportsIcons = UtilityHelper.sportIconsSupplier.get();

        long nonOlympianCount = sportsIcons.stream()
                .filter(s -> !s.isOlampian())
                .count();

        assertEquals(3, nonOlympianCount);
        assertTrue(sportsIcons.stream().anyMatch(s -> "Lionel".equals(s.getName()) && !s.isOlampian()));
    }

    @Test
    void testEmployeeSupplier_shouldReturnListOfEmployees() {
        List<Employee> employees = UtilityHelper.employeeSupplier.get();

        assertNotNull(employees);
        assertEquals(2, employees.size());
    }

    @Test
    void testEmployeeSupplier_shouldReturnEmployeesWithCompleteData() {
        List<Employee> employees = UtilityHelper.employeeSupplier.get();

        Employee santhosh = employees.get(0);
        assertEquals("Santhosh", santhosh.getFirstName());
        assertEquals("Vernekar", santhosh.getLastName());
        assertEquals(30, santhosh.getAge());
        assertEquals(0, santhosh.getNoOfChildren());
        assertTrue(santhosh.isSpouse());
        
        assertNotNull(santhosh.getAddress());
        assertEquals("WhiteField", santhosh.getAddress().getStreetAddress());
        assertEquals("Bengaluru", santhosh.getAddress().getCity());
        assertEquals("Karnataka", santhosh.getAddress().getState());
        assertEquals("India", santhosh.getAddress().getCountry());
        assertEquals("560010", santhosh.getAddress().getPostalCode());
        
        assertNotNull(santhosh.getHobbies());
        assertEquals(2, santhosh.getHobbies().size());
        assertTrue(santhosh.getHobbies().contains("Travelling"));
        
        assertNotNull(santhosh.getPhoneNumbers());
        assertEquals(1, santhosh.getPhoneNumbers().size());
        assertEquals("1234567890", santhosh.getPhoneNumbers().get(0).getNumber());
    }

    @Test
    void testEmployeeSupplier_shouldReturnViratWithCorrectData() {
        List<Employee> employees = UtilityHelper.employeeSupplier.get();

        Employee virat = employees.get(1);
        assertEquals("Virat", virat.getFirstName());
        assertEquals("Kohli", virat.getLastName());
        assertEquals(28, virat.getAge());
        
        assertNotNull(virat.getAddress());
        assertEquals("Delhi Road", virat.getAddress().getStreetAddress());
        assertEquals("Bangalore", virat.getAddress().getCity());
        
        assertNotNull(virat.getPhoneNumbers());
        assertEquals(1, virat.getPhoneNumbers().size());
        assertEquals("1234555555", virat.getPhoneNumbers().get(0).getNumber());
        
        assertNotNull(virat.getHobbies());
        assertTrue(virat.getHobbies().contains("Cricket"));
    }

    @Test
    void testUtilityHelper_privateConstructor() {
        assertThrows(IllegalAccessException.class, () -> {
            var constructor = UtilityHelper.class.getDeclaredConstructor();
            constructor.setAccessible(false);
            constructor.newInstance();
        });
    }
}