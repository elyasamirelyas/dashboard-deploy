package com.demo.bankapp.repository;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.data.rest.core.annotation.RepositoryRestResource;
import com.demo.bankapp.model.Transfer;
@RepositoryRestResource(exported = false)
public interface TransferRepository extends JpaRepository<Transfer, Long> {
        @Query(value = "SELECT t FROM Transfer t WHERE t.fromUserId = :userId and t.transferTime >= TIMESTAMPADD(DAY, -1, CURRENT_TIMESTAMP)")
        List<Transfer> findAllTransfersFrom24Hours(@Param("userId") Long userId);
}