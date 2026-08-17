package com.spring.crud.demo.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.io.Serializable;

@Data
@AllArgsConstructor
@NoArgsConstructor
@Builder
@Entity
@Table
public class Student implements Serializable {

	@Id
	@GeneratedValue
	private int id;

	private int rollNo;
	private String firstName;
	private String lastName;
	private float marks;

	public Student(int rollNo, String firstName, String lastName, float marks) {
		this.rollNo= rollNo;
		this.firstName = firstName;
		this.lastName = lastName;
		this.marks = marks;
	}
}
