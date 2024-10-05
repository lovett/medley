import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HTTP_INTERCEPTORS, provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { ReactiveFormsModule } from '@angular/forms';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { AccountMenuComponent } from './account-menu/account-menu.component';
import { TransactionListComponent } from './transaction-list/transaction-list.component';
import { AccountListComponent } from './account-list/account-list.component';
import { AccountFormComponent } from './account-form/account-form.component';
import { PageNotFoundComponent } from './page-not-found/page-not-found.component';
import { DeleteButtonComponent } from './delete-button/delete-button.component';
import { AddButtonComponent } from './add-button/add-button.component';
import { TransactionFormComponent } from './transaction-form/transaction-form.component';
import { MoneyPipe } from './money.pipe';
import { CacheInterceptor } from './interceptors/cache.interceptor';
import { TagListComponent } from './tag-list/tag-list.component';
import { SelectionSummaryComponent } from './selection-summary/selection-summary.component';

@NgModule({ declarations: [
        AppComponent,
        AccountMenuComponent,
        TransactionListComponent,
        AccountListComponent,
        AccountFormComponent,
        PageNotFoundComponent,
        DeleteButtonComponent,
        AddButtonComponent,
        TransactionFormComponent,
        MoneyPipe,
        TagListComponent,
        SelectionSummaryComponent
    ],
    bootstrap: [AppComponent], imports: [BrowserModule,
        AppRoutingModule,
        ReactiveFormsModule], providers: [
        MoneyPipe,
        { provide: HTTP_INTERCEPTORS, useClass: CacheInterceptor, multi: true },
        provideHttpClient(withInterceptorsFromDi()),
    ] })
export class AppModule { }
