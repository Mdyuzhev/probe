import io.restassured.RestAssured;
import io.restassured.builder.RequestSpecBuilder;
import io.restassured.http.ContentType;
import io.restassured.specification.RequestSpecification;
import org.junit.jupiter.api.BeforeAll;

public class BaseTest {

    protected static RequestSpecification baseSpec;
    protected static RequestSpecification operatorSpec;
    protected static RequestSpecification managerSpec;
    protected static RequestSpecification adminSpec;

    protected static final String OPERATOR_TOKEN = "Bearer eyJhbGciOiJIUzI1NiJ9.operator";
    protected static final String MANAGER_TOKEN  = "Bearer eyJhbGciOiJIUzI1NiJ9.manager";
    protected static final String ADMIN_TOKEN    = "Bearer eyJhbGciOiJIUzI1NiJ9.admin";

    @BeforeAll
    static void setUp() {
        RestAssured.baseURI  = "http://localhost";
        RestAssured.basePath = "/api/v1";
        RestAssured.port     = 8080;

        baseSpec = new RequestSpecBuilder()
                .setContentType(ContentType.JSON)
                .setAccept(ContentType.JSON)
                .build();

        operatorSpec = new RequestSpecBuilder()
                .addRequestSpecification(baseSpec)
                .addHeader("Authorization", OPERATOR_TOKEN)
                .build();

        managerSpec = new RequestSpecBuilder()
                .addRequestSpecification(baseSpec)
                .addHeader("Authorization", MANAGER_TOKEN)
                .build();

        adminSpec = new RequestSpecBuilder()
                .addRequestSpecification(baseSpec)
                .addHeader("Authorization", ADMIN_TOKEN)
                .build();
    }
}
