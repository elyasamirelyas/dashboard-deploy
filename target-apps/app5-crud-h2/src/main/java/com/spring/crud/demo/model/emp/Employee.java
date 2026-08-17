package com.spring.crud.demo.model.emp;

import com.fasterxml.jackson.annotation.JsonManagedReference;
import lombok.*;

import jakarta.persistence.CascadeType;
import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToMany;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Entity
@Table
public class Employee implements Serializable {

    @Id
    @GeneratedValue
    private int id;
    @Column(name = "first_name")
    private String firstName;
    @Column(name = "last_name")
    private String lastName;
    private int age;

    @Column(name = "no_of_children")
    private int noOfChildren;
    private boolean spouse;

    @JsonManagedReference
    @OneToOne(cascade = { 
        		CascadeType.MERGE,
   	    		CascadeType.PERSIST,
   	    		CascadeType.REMOVE
    })
    @JoinColumn(name="address")
    private Address address;


    @JsonManagedReference
    @OneToMany(fetch = FetchType.LAZY, mappedBy = "employee", 
	    cascade = { 
	    		CascadeType.MERGE,
	    		CascadeType.PERSIST,
	    		CascadeType.REMOVE
    })
    private List<PhoneNumber> phoneNumbers;



    @ElementCollection
    @CollectionTable(name="hobbies", joinColumns = @JoinColumn(name="id"))
    @Column(name="hobby")
    private List<String> hobbies = new ArrayList<>();

}

