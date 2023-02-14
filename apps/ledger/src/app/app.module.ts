import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { ReactiveFormsModule } from '@angular/forms';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { TransactionTableComponent } from './transaction-table/transaction-table.component';
import { AccountMenuComponent } from './account-menu/account-menu.component';
import { TransactionListComponent } from './transaction-list/transaction-list.component';
import { AccountListComponent } from './account-list/account-list.component';
import { AccountFormComponent } from './account-form/account-form.component';
import { PageNotFoundComponent } from './page-not-found/page-not-found.component';
import { DeleteButtonComponent } from './delete-button/delete-button.component';
import { AddButtonComponent } from './add-button/add-button.component';
import { TransactionFormComponent } from './transaction-form/transaction-form.component';

@NgModule({
    declarations: [
        AppComponent,
        TransactionTableComponent,
        AccountMenuComponent,
        TransactionListComponent,
        AccountListComponent,
        AccountFormComponent,
        PageNotFoundComponent,
        DeleteButtonComponent,
        AddButtonComponent,
        TransactionFormComponent
    ],
    imports: [
        BrowserModule,
        HttpClientModule,
        AppRoutingModule,
        ReactiveFormsModule
    ],
    providers: [],
    bootstrap: [AppComponent]
})
export class AppModule { }
