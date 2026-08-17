package com.contrastsecurity.demo.providersearch;

import jakarta.persistence.EntityManager;
import jakarta.persistence.EntityManagerFactory;
import jakarta.persistence.Query;
import java.util.List;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class ProviderSearchDAO {
    @Autowired
    private EntityManagerFactory entityManagerFactory;

    public List<Object[]> getProvidersInZipCode(String zipCode) {
        EntityManager em = entityManagerFactory.createEntityManager();
        String q = "select * from PROVIDERS where public_listing is true and zip_code = '" + zipCode + "'";
        Query query = em.createNativeQuery(q);
        List<Object[]> results = query.getResultList();
        return results;
    }
}


