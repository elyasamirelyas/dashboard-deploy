package com.spring.crud.demo.utils;

import com.spring.crud.demo.model.SportsIcon;
import com.spring.crud.demo.model.Student;
import com.spring.crud.demo.model.emp.Employee;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class UtilityHelperTests {

    @Test
    void testStudentSupplier_returnsListOfStudents() {
        List<Student> students = UtilityHelper.studentSupplier.get();
        
        assertNotNull(students);
        assertEquals(12, students.size());
    }

    @Test
    void testStudentSupplier_firstStudentHasCorrectData() {
        List<Student> students = UtilityHelper.studentSupplier.get();
        
        Student firstStudent = students.get(0);
        assertNotNull(firstStudent);
        assertEquals(1, firstStudent.getRollNo());
        assertEquals("Santhosh", firstStudent.getFirstName());
        assertEquals("Vernekar", firstStudent.getLastName());
        assertEquals(300.0f, firstStudent.getMarks());
    }

    @Test
    void testStudentSupplier_lastStudentHasCorrectData() {
        List<Student> students = UtilityHelper.studentSupplier.get();
        
        Student lastStudent = students.get(11);
        assertNotNull(lastStudent);
        assertEquals(10, lastStudent.getRollNo());
        assertEquals("Rishab", lastStudent.getFirstName());
        assertEquals("Shetty", lastStudent.getLastName());
        assertEquals(800.0f, lastStudent.getMarks());
    }

    @Test
    void testSportIconsSupplier_returnsListOfSportsIcons() {
        List<SportsIcon> sportsIcons = UtilityHelper.sportIconsSupplier.get();
        
        assertNotNull(sportsIcons);
        assertEquals(7, sportsIcons.size());
    }

    @Test
    void testSportIconsSupplier_firstIconHasCorrectData() {
        List<SportsIcon> sportsIcons = UtilityHelper.sportIconsSupplier.get();
        
        SportsIcon firstIcon = sportsIcons.get(0);
        assertNotNull(firstIcon);
        assertEquals("Virat", firstIcon.getName());
        assertEquals("King Kohli", firstIcon.getSpecialName());
        assertEquals("Cricketer", firstIcon.getSports());
        assertEquals(33, firstIcon.getAge());
        assertFalse(firstIcon.isOlampian());
    }

    @Test
    void testSportIconsSupplier_olympianIconExists() {
        List<SportsIcon> sportsIcons = UtilityHelper.sportIconsSupplier.get();
        
        SportsIcon neeraj = sportsIcons.get(1);
        assertNotNull(neeraj);
        assertEquals("Neeraj", neeraj.getName());
        assertTrue(neeraj.isOlampian());
    }

    @Test
    void testEmployeeSupplier_returnsListOfEmployees() {
        List<Employee> employees = UtilityHelper.employeeSupplier.get();
        
        assertNotNull(employees);
        assertEquals(2, employees.size());
    }

    @Test
    void testEmployeeSupplier_firstEmployeeHasCorrectData() {
        List<Employee> employees = UtilityHelper.employeeSupplier.get();
        
        Employee firstEmployee = employees.get(0);
        assertNotNull(firstEmployee);
        assertEquals(1, firstEmployee.getId());
        assertEquals("Santhosh", firstEmployee.getFirstName());
        assertEquals("Vernekar", firstEmployee.getLastName());
        assertEquals(30, firstEmployee.getAge());
        assertEquals(0, firstEmployee.getNoOfChildren());
        assertTrue(firstEmployee.isSpouse());
    }

    @Test
    void testEmployeeSupplier_employeeHasAddress() {
        List<Employee> employees = UtilityHelper.employeeSupplier.get();
        
        Employee employee = employees.get(0);
        assertNotNull(employee.getAddress());
        assertEquals("WhiteField", employee.getAddress().getStreetAddress());
        assertEquals("Bengaluru", employee.getAddress().getCity());
        assertEquals("Karnataka", employee.getAddress().getState());
        assertEquals("India", employee.getAddress().getCountry());
        assertEquals("560010", employee.getAddress().getPostalCode());
    }

    @Test
    void testEmployeeSupplier_employeeHasPhoneNumbers() {
        List<Employee> employees = UtilityHelper.employeeSupplier.get();
        
        Employee employee = employees.get(0);
        assertNotNull(employee.getPhoneNumbers());
        assertEquals(1, employee.getPhoneNumbers().size());
        assertEquals("Mobile", employee.getPhoneNumbers().get(0).getType());
        assertEquals("1234567890", employee.getPhoneNumbers().get(0).getNumber());
    }

    @Test
    void testEmployeeSupplier_employeeHasHobbies() {
        List<Employee> employees = UtilityHelper.employeeSupplier.get();
        
        Employee employee = employees.get(0);
        assertNotNull(employee.getHobbies());
        assertEquals(2, employee.getHobbies().size());
        assertTrue(employee.getHobbies().contains("Travelling"));
        assertTrue(employee.getHobbies().contains("Sports"));
    }

    @Test
    void testSuppliers_returnNewListsOnEachInvocation() {
        List<Student> students1 = UtilityHelper.studentSupplier.get();
        List<Student> students2 = UtilityHelper.studentSupplier.get();
        
        assertNotSame(students1, students2);
        assertEquals(students1.size(), students2.size());
    }

    @Test
    void testEmployeeSupplier_secondEmployeeHasCorrectData() {
        List<Employee> employees = UtilityHelper.employeeSupplier.get();
        
        Employee secondEmployee = employees.get(1);
        assertNotNull(secondEmployee);
        assertEquals("Virat", secondEmployee.getFirstName());
        assertEquals("Kohli", secondEmployee.getLastName());
        assertEquals(28, secondEmployee.getAge());
        assertNotNull(secondEmployee.getPhoneNumbers());
        assertEquals("1234555555", secondEmployee.getPhoneNumbers().get(0).getNumber());
    }
}