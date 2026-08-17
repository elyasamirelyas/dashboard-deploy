package demo;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.test.context.junit.jupiter.SpringExtension;
import org.springframework.test.context.web.WebAppConfiguration;

import com.demo.BootDemoApplication;

import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(classes = BootDemoApplication.class)
@WebAppConfiguration
public class BootDemoApplicationTests {

	@Test
	public void contextLoads() {
	}

}
