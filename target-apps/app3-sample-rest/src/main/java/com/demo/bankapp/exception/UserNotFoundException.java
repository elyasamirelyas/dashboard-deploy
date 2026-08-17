package com.demo.bankapp.exception;

import java.io.Serial;

public class UserNotFoundException extends RuntimeException {

	@Serial
	private static final long serialVersionUID = -1360953961105975949L;

	public UserNotFoundException() {
		super("User wealth not found");
	}

	public UserNotFoundException(String username) {
		super("Could not find user " + username);
	}

}
